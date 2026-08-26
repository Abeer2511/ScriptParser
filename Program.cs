using System;
using System.IO;
using System.Linq;
using Storyboard_Studio_Script_Parser;
using Storyboard_Studio_Script_Parser.Services;

if (args.Length == 0 || string.IsNullOrWhiteSpace(args[0]))
{
    Console.ForegroundColor = ConsoleColor.Red;
    Console.WriteLine("Error: Script name is required.");
    Console.ResetColor();
    Console.WriteLine("Usage: dotnet run -- <script_name>");
    PrintAvailableScripts(FindScriptsDirectory());
    return 1;
}

string scriptsDir = FindScriptsDirectory();
if (!Directory.Exists(scriptsDir))
{
    Console.ForegroundColor = ConsoleColor.Red;
    Console.WriteLine($"Error: Scripts directory not found at '{scriptsDir}'.");
    Console.ResetColor();
    return 1;
}

string targetName = args[0].Trim();
if (targetName.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
{
    targetName = Path.GetFileNameWithoutExtension(targetName);
}

var jsonFiles = Directory.GetFiles(scriptsDir, "*.json");
string? matchedFilePath = jsonFiles.FirstOrDefault(f => 
    string.Equals(Path.GetFileNameWithoutExtension(f), targetName, StringComparison.OrdinalIgnoreCase));

if (matchedFilePath == null)
{
    Console.ForegroundColor = ConsoleColor.Red;
    Console.WriteLine($"Error: Script '{targetName}.json' was not found in '{scriptsDir}'.");
    Console.ResetColor();
    PrintAvailableScripts(scriptsDir);
    return 1;
}

string scriptName = Path.GetFileNameWithoutExtension(matchedFilePath);
string projectRoot = Directory.GetParent(scriptsDir)?.FullName ?? Directory.GetCurrentDirectory();

string exportRoot = Path.Combine(projectRoot, "Exports", scriptName);
string markdownOutputPath = Path.Combine(exportRoot, "Markdowns");
string imageOutputPath = Path.Combine(exportRoot, "Images");
string videoPromptsOutputPath = Path.Combine(exportRoot, "VideoPrompts");

Console.WriteLine($"==> Processing script: {scriptName}");
Console.WriteLine($"    Source: {matchedFilePath}");
Console.WriteLine($"    Export destination: {exportRoot}");

Directory.CreateDirectory(markdownOutputPath);
Directory.CreateDirectory(imageOutputPath);
Directory.CreateDirectory(videoPromptsOutputPath);

var script = ReadScriptService.ReadScript(matchedFilePath);
if (script == null)
{
    Console.ForegroundColor = ConsoleColor.Red;
    Console.WriteLine($"Error: Failed to deserialize '{matchedFilePath}'.");
    Console.ResetColor();
    return 1;
}

var (simplifiedScript, imageTracker) = TransformationService.TransformToSimplifiedModel(script);

string mdFilePath = Path.Combine(markdownOutputPath, $"{scriptName}.md");
MarkdownConverterService.ConvertJsonFileToMarkdown(simplifiedScript, mdFilePath);

Console.WriteLine($"==> Reconstructing {imageTracker.Count} images from base64...");
await new ImageReconstructionService().ReconstructImagesFromBase64(imageTracker, imageOutputPath);

Console.ForegroundColor = ConsoleColor.Green;
Console.WriteLine($"\n[SUCCESS] Extraction complete for '{scriptName}':");
Console.WriteLine($"  - Markdown: {mdFilePath}");
Console.WriteLine($"  - Images:   {imageOutputPath}");
Console.ResetColor();

return 0;

static string FindScriptsDirectory()
{
    string current = Directory.GetCurrentDirectory();
    if (Directory.Exists(Path.Combine(current, "Scripts")))
    {
        return Path.Combine(current, "Scripts");
    }

    var dir = new DirectoryInfo(AppContext.BaseDirectory);
    while (dir != null)
    {
        string candidate = Path.Combine(dir.FullName, "Scripts");
        if (Directory.Exists(candidate))
        {
            return candidate;
        }
        dir = dir.Parent;
    }

    return Path.Combine(current, "Scripts");
}

static void PrintAvailableScripts(string scriptsDir)
{
    if (Directory.Exists(scriptsDir))
    {
        var files = Directory.GetFiles(scriptsDir, "*.json")
            .Select(Path.GetFileNameWithoutExtension)
            .ToList();

        if (files.Count > 0)
        {
            Console.WriteLine("\nAvailable scripts in Scripts folder:");
            foreach (var f in files)
            {
                Console.WriteLine($"  - {f}");
            }
        }
        else
        {
            Console.WriteLine("\nNo .json files found in the Scripts directory.");
        }
    }
}
