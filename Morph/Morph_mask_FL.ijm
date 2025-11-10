input = getDirectory("Fluorescent Image");
output = getDirectory("morphological masks");

list = getFileList(input);

for (i = 0; i < list.length; i++) {
			open(input+list[i]);
			
			setAutoThreshold("Default dark no-reset");
			run("Threshold...");
			run("Convert to Mask");
			run("Fill Holes");
			run("Options...", "iterations=5 count=3 black do=Nothing");
			run("Close-");
			//save image
			name = replace(list[i], ".tif", "");
        	saveAs("Tiff", output + name + "_mask.tif");
			run("Close All");
}