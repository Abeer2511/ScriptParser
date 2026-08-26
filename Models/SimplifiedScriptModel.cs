using System;
using System.Collections.Generic;
using System.Text;

namespace Storyboard_Studio_Script_Parser.Models
{
    public class SimplifiedScriptModel
    {
        public string title { get; set; } = string.Empty;
        public string fullStory { get; set; } = string.Empty;
        public List<Character> characters { get; set; } = [];
        public List<Location> locations { get; set; } = [];
        public List<Prop> props { get; set; } = [];
        public List<Scene> scenes { get; set; } = [];
    }

    public class Character
    {
        public string id { get; set; } = string.Empty;
        public string name { get; set; } = string.Empty;
        public string type { get; set; } = string.Empty;
        public string physicalCharacteristics { get; set; } = string.Empty;
        public string clothingAccessories { get; set; } = string.Empty;
        public string backstory { get; set; } = string.Empty;
    }

    public class Location
    {
        public string id { get; set; } = string.Empty;
        public string name { get; set; } = string.Empty;
        public string type { get; set; } = string.Empty;
    }

    public class Prop
    {
        public string id { get; set; } = string.Empty;
        public string name { get; set; } = string.Empty;
        public string type { get; set; } = string.Empty;
    }

    public class Scene
    {
        public int sceneNumber { get; set; }
        public string sceneTitle { get; set; } = string.Empty;
        public List<Shot> shots { get; set; } = [];
    }

    public class Shot
    {
        public string shotNumber { get; set; } = string.Empty;
        public string title { get; set; } = string.Empty;
        public string visualDescription { get; set; } = string.Empty;
        public string audioDescription { get; set; } = string.Empty;
        public string motionDescription { get; set; } = string.Empty;
        public HashSet<string> linkedAssetIds { get; set; } = [];
    }
}
