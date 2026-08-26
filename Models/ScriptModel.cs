using System;
using System.Collections.Generic;
using System.Text;

namespace Storyboard_Studio_Script_Parser.Models
{
    public class ScriptModel
    {
        public string projectTitle { get; set; } = string.Empty;
        public string fullMarkdown { get; set; } = string.Empty;
        public string globalStyle { get; set; } = string.Empty;
        public List<Assets> assets { get; set; } = [];
        public List<Frames> frames { get; set; } = [];
    }

    public class Assets
    {
        public string id { get; set; } = string.Empty;
        public string type { get; set; } = string.Empty;
        public string name { get; set; } = string.Empty;
        public string physicalCharacteristics { get; set; } = string.Empty;
        public string clothingAccessories { get; set; } = string.Empty;
        public string backstory { get; set; } = string.Empty;
        public List<SupportingImages> supportingImages { get; set; } = [];
    }

    public class Frames
    {
        public string id { get; set; } = string.Empty;
        public string sceneId { get; set; } = string.Empty;
        public string sceneNumber { get; set; } = string.Empty;
        public string sceneTitle { get; set; } = string.Empty;
        public string shotNumber { get; set; } = string.Empty;
        public string title { get; set; } = string.Empty;
        public string visualDescription { get; set; } = string.Empty;
        public string audioDescription { get; set; } = string.Empty;
        public string motionDescription { get; set; } = string.Empty;
        public string base64 { get; set; } = string.Empty;
        public List<string> linkedAssetIds { get; set; } = [];

    }

    public class SupportingImages
    {
        public string base64 { get; set; } = string.Empty;
    }
}
