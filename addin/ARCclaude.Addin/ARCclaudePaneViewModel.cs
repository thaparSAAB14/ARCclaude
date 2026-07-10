using System;
using System.Collections.ObjectModel;
using System.Windows.Input;
using ArcGIS.Desktop.Framework;
using ArcGIS.Desktop.Framework.Contracts;

namespace ARCclaude.Addin
{
    public class LogEntry
    {
        public string Timestamp { get; set; }
        public string Message { get; set; }
        public string Color { get; set; }
    }

    internal class ARCclaudePaneViewModel : DockPane
    {
        private const string DockPaneId = "ARCclaude_Pane";

        public ObservableCollection<LogEntry> Activity { get; } = new();

        private bool _listening;
        public bool Listening
        {
            get => _listening;
            set
            {
                if (SetProperty(ref _listening, value))
                {
                    if (value) LiveLinkService.Start(); else LiveLinkService.Stop();
                    NotifyPropertyChanged(nameof(StatusText));
                    NotifyPropertyChanged(nameof(StatusColor));
                }
            }
        }

        public string StatusText => Listening
            ? "Cowork Active (AI Connected)"
            : "Cowork Inactive (Offline)";

        public string StatusColor => Listening ? "#E2E8F0" : "#64748B";


        public ICommand ClearCommand { get; }

        protected ARCclaudePaneViewModel()
        {
            ClearCommand = new RelayCommand(() => Activity.Clear());
            LiveLinkService.Log += line =>
                System.Windows.Application.Current.Dispatcher.Invoke(() =>
                {
                    Activity.Add(CreateLogEntry(line));
                    while (Activity.Count > 500) Activity.RemoveAt(0);
                });
            Activity.Add(new LogEntry
            {
                Timestamp = $"[{DateTime.Now:HH:mm:ss}]",
                Message = "ARCclaude add-in loaded. Toggle cowork mode to let the AI in.",
                Color = "#808080"
            });
        }

        private static LogEntry CreateLogEntry(string line)
        {
            string color = "#F1F1F1"; // Default off-white/light gray
            if (line.Contains("-> ok") || line.Contains("success") || line.Contains("ACTIVE"))
            {
                color = "#4EC9B0"; // Green/Teal
            }
            else if (line.Contains("ERROR") || line.Contains("failed") || line.Contains("exception"))
            {
                color = "#F44747"; // Red
            }
            else if (line.Contains("⚙ executing"))
            {
                color = "#9CDCFE"; // Cyan/Blue
            }
            else if (line.Contains("stopped") || line.Contains("heartbeat"))
            {
                color = "#808080"; // Muted Gray
            }

            return new LogEntry
            {
                Timestamp = $"[{DateTime.Now:HH:mm:ss}]",
                Message = line,
                Color = color
            };
        }

        internal static void Show()
        {
            var pane = FrameworkApplication.DockPaneManager.Find(DockPaneId);
            pane?.Activate();
        }
    }
}
