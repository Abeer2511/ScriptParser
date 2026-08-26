using Storyboard_Studio_Script_Parser.Models;
using System;
using System.Collections.Generic;
using System.Text;

namespace Storyboard_Studio_Script_Parser.Services
{
    public class ImageReconstructionService
    {
        public async Task ReconstructImagesFromBase64(List<Base64StringModel> base64Strings, string imageOutputPath)
        {
            string fileExtension = ".jpg";

            Directory.CreateDirectory(Path.Combine(imageOutputPath, Base64StringType.Character.ToString()));
            Directory.CreateDirectory(Path.Combine(imageOutputPath, Base64StringType.Location.ToString()));
            Directory.CreateDirectory(Path.Combine(imageOutputPath, Base64StringType.Prop.ToString()));
            Directory.CreateDirectory(Path.Combine(imageOutputPath, Base64StringType.Frame.ToString()));

            char[] invalidChars = Path.GetInvalidFileNameChars();

            int index = 0;
            foreach (var item in base64Strings)
            {
                index++;
                if (string.IsNullOrWhiteSpace(item.base64)) continue;

                string rawName = string.IsNullOrWhiteSpace(item.nameTag) ? $"image_{index}" : item.nameTag;
                string safeName = string.Concat(rawName.Split(invalidChars, StringSplitOptions.None));
                if (string.IsNullOrWhiteSpace(safeName)) safeName = $"image_{index}";

                string fullFilePath = Path.Combine(imageOutputPath, item.type.ToString(), $"{safeName}{fileExtension}");
                
                try
                {
                    byte[] imageBytes = Convert.FromBase64String(item.base64);
                    await File.WriteAllBytesAsync(fullFilePath, imageBytes);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Warning: Failed to save image '{safeName}': {ex.Message}");
                }
            }
        }
    }
}
