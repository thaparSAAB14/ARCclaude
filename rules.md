# ARCclaude Development Guidelines & Rules

Use these rules when making changes or performing tasks inside ArcGIS Pro.

## 1. File & Project Management
* **No New `.aprx` Files:** Never create or save new `.aprx` project files unless explicitly requested. Work entirely within the currently open project.
* **No Duplicate Maps or Layouts:** Do not duplicate maps or layout tabs for the same dataset. If a change can be achieved by updating symbology or properties (e.g., using a UniqueValueRenderer), do that instead of creating separate layers or maps.
* **No New Layers:** Do not create or copy new layers in the map unless explicitly prompted to do so.

## 2. User Experience & Live Interaction
* **Show Changes Instantly:** Always open the modified tabs (map tabs, layout tabs) immediately after making programmatic updates using `openView()`. This ensures changes are shown live to the user without requiring manual refreshes.
* **Human-Readable Action Messages:** When reporting progress, actions, or logs, avoid displaying raw numbers or code block steps. Always describe the actions in human-readable terms matching the respective tool (e.g., *"Applying symbology..."*, *"Calculating buffer..."*, *"Exporting features..."*).

## 3. UI & Add-in Enhancement Goals
* **Vibrant & Visual Interface:** Add visual colors, interactive elements, and micro-animations to the add-in to ensure a premium look and feel.

## 4. Multi-Agent & Orchestrated Processing
* **Multi-Agent Delegation:** Use multi-agent coordination or a hierarchical "boss/worker" model to parallelize data retrieval, analysis, and processing tasks for faster performance.

## 5. Non-Technical Accessibility & Self-Healing Code
* **Self-Healing Automation:** Programmatic scripts must anticipate non-technical user context issues. Proactively validate schema limits (e.g., field name lengths), layer ordering, and spatial coordinate systems. If a mismatch is found, automatically repair it (e.g., changing map spatial reference to match data) rather than failing.
* **Friendly & Jargon-Free Logging:** Translate complex GIS exceptions and logs into plain, descriptive language. Explain the "why" and "how" of any auto-corrections so that non-technical users can follow along without needing deep GIS expertise.

