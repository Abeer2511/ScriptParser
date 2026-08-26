using System;
using System.Buffers.Text;
using System.Collections.Generic;
using System.Text;

namespace Storyboard_Studio_Script_Parser.Models
{
    public class Base64StringModel
    {
        public string base64 { get; set; }
        public Base64StringType type { get; set; }
        public string nameTag { get; set; }


        public Base64StringModel(string base64, Base64StringType type, string nameTag)
        {
            this.base64 = base64;
            this.type = type;
            this.nameTag = nameTag;
        }
    }

    public enum Base64StringType
    {
        Frame,
        Prop,
        Character,
        Location
    }
}
