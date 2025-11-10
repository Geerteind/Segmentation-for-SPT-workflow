input = getDirectory("BrightField Images");
output = getDirectory("Store morphological masks");

list = getFileList(input);

		for (i = 0; i < list.length; i++) {
			open(input+list[i]);
			//Image processing
			setOption("ScaleConversions", true);
			run("16-bit");
			run("Enhance Contrast...", "saturated=0 equalize");
			run("3D Edge and Symmetry Filter", "alpha=0.250 radius=1.75 normalization=10 scaling=2 improved");
			selectWindow("Edges");
			run("Maximum...", "radius=5");
			setOption("BlackBackground", true);
			run("Convert to Mask");
			run("Maximum...", "radius=5");
			run("Options...", "iterations=10 count=3 black do=Nothing");
			run("Close-");
			run("Fill Holes");
			run("Options...", "iterations=10 count=3 black do=Nothing");
			run("Open");
			run("Options...", "iterations=1 count=3 black do=Nothing");
			run("Erode");
			name = replace(list[i], ".tif", "");
        	saveAs("Tiff", output + name + "_mask.tif");
			run("Close All");
			}