using ArcGIS.Desktop.Framework;
using ArcGIS.Desktop.Framework.Contracts;

namespace ARCclaude.Addin
{
    internal class Module1 : Module
    {
        private static Module1 _this;

        public static Module1 Current =>
            _this ??= (Module1)FrameworkApplication.FindModule("ARCclaude_Module");

        protected override bool CanUnload()
        {
            LiveLinkService.Stop();
            return true;
        }
    }
}
