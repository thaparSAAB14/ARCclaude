using System.Collections.ObjectModel;
using System.Windows.Input;
using ArcGIS.Desktop.Framework;
using ArcGIS.Desktop.Framework.Contracts;

namespace ARCclaude.Addin
{
    internal class ARCclaudePaneViewModel : DockPane
    {
        private const string DockPaneId = "ARCclaude_Pane";

        public ObservableCollection<string> Activity { get; } = new();

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
                }
            }
        }

        public string StatusText => Listening
            ? "● Cowork ON — AI assistants can drive this session"
            : "○ Cowork off";

        public ICommand ClearCommand { get; }

        protected ARCclaudePaneViewModel()
        {
            ClearCommand = new RelayCommand(() => Activity.Clear());
            LiveLinkService.Log += line =>
                System.Windows.Application.Current.Dispatcher.Invoke(() =>
                {
                    Activity.Add($"[{DateTime.Now:HH:mm:ss}] {line}");
                    while (Activity.Count > 500) Activity.RemoveAt(0);
                });
            Activity.Add("ARCclaude add-in loaded. Toggle cowork mode to let the AI in.");
        }

        internal static void Show()
        {
            var pane = FrameworkApplication.DockPaneManager.Find(DockPaneId);
            pane?.Activate();
        }
    }
}
