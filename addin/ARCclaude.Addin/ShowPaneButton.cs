using ArcGIS.Desktop.Framework.Contracts;

namespace ARCclaude.Addin
{
    internal class ShowPaneButton : Button
    {
        protected override void OnClick() => ARCclaudePaneViewModel.Show();
    }
}
