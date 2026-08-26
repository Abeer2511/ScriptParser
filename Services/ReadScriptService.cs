using Storyboard_Studio_Script_Parser.Models;
using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;

namespace Storyboard_Studio_Script_Parser.Services
{
    public static class ReadScriptService
    {
        public static ScriptModel? ReadScript(string filePath)
        {
            try
            {
                string jsonString = File.ReadAllText(filePath);
                ScriptModel? script = JsonSerializer.Deserialize<ScriptModel>(jsonString);
                return script;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error reading script: {ex.Message}");
                return null;
            }
        }
    }
}
