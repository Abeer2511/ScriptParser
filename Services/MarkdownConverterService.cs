using System;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Linq;
using Storyboard_Studio_Script_Parser.Models; // Ensure this matches your namespace

namespace Storyboard_Studio_Script_Parser
{
    public class MarkdownConverterService
    {
        public static void ConvertJsonFileToMarkdown(SimplifiedScriptModel scriptModel, string outputMdFilePath)
        {
            if (scriptModel == null)
            {
                Console.WriteLine("Failed to parse JSON.");
                return;
            }

            // 2. Build the Markdown content
            StringBuilder md = new();

            // Project Title
            md.AppendLine($"## Title: {scriptModel.title}");
            md.AppendLine();

            //Full Story Section
            md.AppendLine($"## Full Story: {scriptModel.fullStory}");
            md.AppendLine();

            // Characters Section
            if (scriptModel.characters != null && scriptModel.characters.Count > 0)
            {
                md.AppendLine("# Assets");
                md.AppendLine("## Characters");
                md.AppendLine();
                foreach (var character in scriptModel.characters)
                {
                    md.AppendLine($"### {character.name}");
                    if (!string.IsNullOrWhiteSpace(character.physicalCharacteristics))
                        md.AppendLine($"- **Physical Characteristics:** {character.physicalCharacteristics}");
                    if (!string.IsNullOrWhiteSpace(character.clothingAccessories))
                        md.AppendLine($"- **Clothing/Accessories:** {character.clothingAccessories}");
                    if (!string.IsNullOrWhiteSpace(character.backstory))
                        md.AppendLine($"- **Backstory:** {character.backstory}");
                    md.AppendLine();
                }
            }

            // Locations Section
            if (scriptModel.locations != null && scriptModel.locations.Count > 0)
            {
                md.AppendLine("## Locations");
                md.AppendLine();
                foreach (var loc in scriptModel.locations)
                {
                    md.AppendLine($"- **{loc.name}**");
                }
                md.AppendLine();
            }

            // Props Section
            if(scriptModel.props != null && scriptModel.props.Count > 0)
            {
                md.AppendLine("## Props");
                md.AppendLine();
                foreach (var prop in scriptModel.props)
                {
                    md.AppendLine($"- **{prop.name}**");
                }
                md.AppendLine();
            }

            // Scenes & Shots Section
            if (scriptModel.scenes != null && scriptModel.scenes.Count > 0)
            {
                md.AppendLine("## Scenes");
                md.AppendLine();
                foreach (var scene in scriptModel.scenes)
                {
                    md.AppendLine($"### Scene {scene.sceneNumber}: {scene.sceneTitle}");
                    md.AppendLine();

                    if (scene.shots != null)
                    {
                        foreach (var shot in scene.shots)
                        {
                            md.AppendLine($"#### Shot {shot.shotNumber}: {shot.title}");
                            
                            // Visual Section
                            md.AppendLine($"- **Visual:**");
                            md.AppendLine($"  > {shot.visualDescription}");

                            // Audio Section
                            md.AppendLine($"- **Audio:**");
                            md.AppendLine($"  > {shot.audioDescription}");

                            // Motion Section (Only if it exists)
                            if (!string.IsNullOrWhiteSpace(shot.motionDescription))
                            {
                                md.AppendLine($"- **Motion:**");
                                md.AppendLine($"  > {shot.motionDescription}");
                            }

                            // Linked Assets (Rendered as an indented sub-list)
                            if (shot.linkedAssetIds != null && shot.linkedAssetIds.Count > 0)
                            {
                                md.AppendLine($"- **Assets:**");
                                foreach (var asset in shot.linkedAssetIds)
                                {
                                    md.AppendLine($"  - `{asset}`");
                                }
                            }

                            // Add extra spacing between shots
                            md.AppendLine();
                            md.AppendLine("---"); // Optional horizontal line separator between shots
                            md.AppendLine();
                        }
                    }
                }
            }

            // 3. Write to the .md file
            File.WriteAllText(outputMdFilePath, md.ToString());
            Console.WriteLine($"Successfully generated Markdown file at: {outputMdFilePath}");
        }
    }
}