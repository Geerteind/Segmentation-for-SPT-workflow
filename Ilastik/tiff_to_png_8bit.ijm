input = getDirectory("Tiff Images");
output = getDirectory("PNG Images")

list = getFileList(input);

for (i=0; i < list.length; i++) { 
	open(input + list[i]);
	run("8-bit");
	run("Fill Holes");
	//save image
	name = replace(list[i], ".tif", "");
    saveAs("png", output + name + "_mask.png");
	run("Close All");
}
