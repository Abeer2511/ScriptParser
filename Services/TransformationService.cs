using Storyboard_Studio_Script_Parser.Models;
using System;
using System.Collections.Generic;
using System.Text;

namespace Storyboard_Studio_Script_Parser.Services
{
    public static class TransformationService
    {
        private const string CharacterType = "character";
        private const string LocationType = "location";
        private const string PropType = "prop";


        public static (SimplifiedScriptModel, List<Base64StringModel>) TransformToSimplifiedModel(ScriptModel scriptModel)
        {
            SimplifiedScriptModel model = new()
            {
                title = scriptModel.projectTitle,
                fullStory = scriptModel.fullMarkdown,
                characters = [],
                locations = [],
                scenes = []
            };

            List<Base64StringModel> imageTracker = new();

            foreach (var assets in scriptModel.assets)
            {
                if (assets.type == CharacterType)
                {
                    model.characters.Add(new Character
                    {
                        id = assets.id,
                        name = assets.name,
                        type = assets.type,
                        physicalCharacteristics = assets.physicalCharacteristics,
                        clothingAccessories = assets.clothingAccessories,
                        backstory = assets.backstory
                    });

                    if (assets.supportingImages != null && !string.IsNullOrEmpty(assets.supportingImages.FirstOrDefault()?.base64))
                    {
                        imageTracker.Add(new Base64StringModel(
                            assets.supportingImages.FirstOrDefault()?.base64 ?? string.Empty,
                            Base64StringType.Character,
                            assets.name
                        ));
                    }
                }
                else if (assets.type == LocationType)
                {
                    model.locations.Add(new Location
                    {
                        id = assets.id,
                        name = assets.name,
                        type = assets.type
                    });

                    if (assets.supportingImages != null && assets.supportingImages.FirstOrDefault()?.base64 != null)
                    {
                        imageTracker.Add(new Base64StringModel(
                            assets.supportingImages.FirstOrDefault()?.base64 ?? string.Empty,
                            Base64StringType.Location,
                            assets.name
                        ));
                    }
                }
                else if (assets.type == PropType)
                {
                    model.props.Add(new Prop
                    {
                        id = assets.id,
                        name = assets.name,
                        type = assets.type
                    });

                    if (assets.supportingImages != null && !string.IsNullOrEmpty(assets.supportingImages.FirstOrDefault()?.base64))
                    {
                        imageTracker.Add(new Base64StringModel(
                            assets.supportingImages.FirstOrDefault()?.base64 ?? string.Empty,
                            Base64StringType.Prop,
                            assets.name
                        ));
                    }
                }
            }

            scriptModel.frames.Where(x=>!string.IsNullOrEmpty(x.base64)).ToList().ForEach(x => imageTracker.Add(new Base64StringModel(
                x.base64,
                Base64StringType.Frame,
                x.title
            )));

            var scenes = scriptModel.frames.GroupBy(f => Convert.ToInt32(f.sceneNumber)).OrderBy(s => s.Key).ToList();

            model.scenes = [.. scenes.Select(s => new Scene
            {
                sceneNumber = s.Key,
                sceneTitle = s.First().sceneTitle,
                shots = [.. s.Select(f => new Shot
                {
                    shotNumber = f.shotNumber,
                    title = f.title,
                    visualDescription = f.visualDescription,
                    audioDescription = f.audioDescription,
                    motionDescription = f.motionDescription,
                    linkedAssetIds = [.. scriptModel.assets.Where(a => f.linkedAssetIds.Contains(a.id)).Select(a => a.name)]
                })]
            })];

            return (model,imageTracker);
        }
    }
}
