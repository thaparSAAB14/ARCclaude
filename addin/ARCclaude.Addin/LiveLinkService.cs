using System.IO;
using System.Text.Json;
using ArcGIS.Desktop.Core.Geoprocessing;

namespace ARCclaude.Addin
{
    /// <summary>
    /// Native host for the ARCclaude Live Link protocol.
    ///
    /// Watches ~/.arcclaude/live for cmd_*.json files dropped by any ARCclaude
    /// client (MCP server tool pro_live_execute, chat CLI), executes each one
    /// inside THIS ArcGIS Pro session via a geoprocessing script tool (which
    /// runs on Pro's in-process Python, where arcpy.mp "CURRENT" works), and
    /// relies on the runner to write result_*.json back. Protocol-compatible
    /// with the v0.3 pasted-Python-window listener, minus the freeze risk:
    /// watching happens in .NET, execution rides the GP queue.
    /// </summary>
    internal static class LiveLinkService
    {
        private static readonly string LiveDir =
            Environment.GetEnvironmentVariable("ARCCLAUDE_LIVE_DIR")
            ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                            ".arcclaude", "live");

        private static FileSystemWatcher _watcher;
        private static System.Timers.Timer _heartbeat;
        private static readonly SemaphoreSlim Gate = new(1, 1);
        private static long _executed;

        public static bool IsRunning { get; private set; }
        public static event Action<string> Log;

        public static void Start()
        {
            if (IsRunning) return;
            Directory.CreateDirectory(LiveDir);

            // purge leftovers so nothing stale ever replays
            foreach (var stale in Directory.GetFiles(LiveDir, "cmd_*")
                                           .Concat(Directory.GetFiles(LiveDir, "result_*"))
                                           .Concat(Directory.GetFiles(LiveDir, "stop")))
            {
                try { File.Delete(stale); } catch (IOException) { } catch (UnauthorizedAccessException) { }
            }

            _watcher = new FileSystemWatcher(LiveDir, "cmd_*.json")
            {
                NotifyFilter = NotifyFilters.FileName | NotifyFilters.LastWrite,
                EnableRaisingEvents = true,
            };
            _watcher.Created += (_, e) => _ = HandleCommandAsync(e.FullPath);
            _watcher.Renamed += (_, e) => _ = HandleCommandAsync(e.FullPath);

            _heartbeat = new System.Timers.Timer(2000) { AutoReset = true };
            _heartbeat.Elapsed += (_, _) => WriteHeartbeat();
            _heartbeat.Start();
            WriteHeartbeat();

            IsRunning = true;
            Log?.Invoke($"Live Link ACTIVE (native host). Queue: {LiveDir}");

            // catch anything that arrived before the watcher existed
            foreach (var pending in Directory.GetFiles(LiveDir, "cmd_*.json"))
                _ = HandleCommandAsync(pending);
        }

        public static void Stop()
        {
            if (!IsRunning) return;
            _watcher?.Dispose(); _watcher = null;
            _heartbeat?.Dispose(); _heartbeat = null;
            try { File.Delete(Path.Combine(LiveDir, "heartbeat")); }
            catch (IOException) { } catch (UnauthorizedAccessException) { }
            IsRunning = false;
            Log?.Invoke($"Live Link stopped ({_executed} commands executed this session).");
        }

        private static void WriteHeartbeat()
        {
            try { File.WriteAllText(Path.Combine(LiveDir, "heartbeat"), DateTimeOffset.Now.ToUnixTimeSeconds().ToString()); }
            catch (IOException) { } catch (UnauthorizedAccessException) { }
        }

        private static async Task HandleCommandAsync(string cmdPath)
        {
            await Gate.WaitAsync();  // arcpy/GP: one command at a time
            try
            {
                if (!File.Exists(cmdPath)) return;   // another handler claimed it

                string id, code;
                try
                {
                    using var doc = JsonDocument.Parse(await ReadWithRetryAsync(cmdPath));
                    id = doc.RootElement.GetProperty("id").GetString();
                    code = doc.RootElement.GetProperty("code").GetString();
                }
                catch (Exception ex) when (ex is JsonException or KeyNotFoundException or IOException)
                {
                    Log?.Invoke($"skipping malformed command {Path.GetFileName(cmdPath)}: {ex.Message}");
                    try { File.Delete(cmdPath); } catch (IOException) { }
                    return;
                }

                try { File.Delete(cmdPath); } catch (IOException) { return; }

                var codeFile = Path.Combine(Path.GetTempPath(), $"arcclaude_live_{id}.py");
                await File.WriteAllTextAsync(codeFile, code);

                Log?.Invoke($"⚙ executing {id} ...");
                var runner = Path.Combine(AddinFolder(), "Runner", "arcclaude_runner.pyt");
                var tool = runner + "\\RunCode";
                var args = Geoprocessing.MakeValueArray(codeFile, LiveDir, id);
                var result = await Geoprocessing.ExecuteToolAsync(
                    tool, args, null, null, null, GPExecuteToolFlags.Default);

                var resultFile = Path.Combine(LiveDir, $"result_{id}.json");
                if (!File.Exists(resultFile))
                {
                    // runner never got far enough to answer — synthesize an error
                    var messages = string.Join("\n",
                        result.Messages.Select(msg => msg.Text));
                    var payload = JsonSerializer.Serialize(new
                    {
                        id, ok = false,
                        error = "Runner produced no result." + (result.IsFailed ? " GP failed." : ""),
                        gp_messages = messages,
                    });
                    var tmp = resultFile + ".tmp";
                    await File.WriteAllTextAsync(tmp, payload);
                    File.Move(tmp, resultFile, overwrite: true);
                }

                _executed++;
                Log?.Invoke($"  {id} -> {(result.IsFailed ? "ERROR" : "ok")}");
                try { File.Delete(codeFile); } catch (IOException) { }
            }
            finally
            {
                Gate.Release();
            }
        }

        private static async Task<string> ReadWithRetryAsync(string path)
        {
            for (var attempt = 0; ; attempt++)
            {
                try { return await File.ReadAllTextAsync(path); }
                catch (IOException) when (attempt < 5) { await Task.Delay(100); }
            }
        }

        private static string AddinFolder() =>
            Path.GetDirectoryName(typeof(LiveLinkService).Assembly.Location);
    }
}
