//Select input directory
input = getDirectory("Input folder")
//modelPath = File.openDialog("Choose trained Weka .model file");
output = getDirectory("Output folder masks");

//Get list of files in the folder
list = getFileList(input);


		for (i = 148; i < list.length; i++) {
			open(input+list[i]);
			run("16-bit");
			
			run("Trainable Weka Segmentation");
			wait(2000);
			call("trainableSegmentation.Weka_Segmentation.loadClassifier", "C:\\Users\\20224105\\OneDrive - TU Eindhoven\\Documents\\TUe\\Year 4\\BEP\\Weka\\classifier\\classifier_Weka_FL.model");
			wait(8000);
			call("trainableSegmentation.Weka_Segmentation.getProbability");
			wait(8000);
			selectWindow("Probability maps");
			
			//post weka processing
			setSlice(1);
			run("Duplicate...", "title=Class_1");
			run("8-bit");
			setAutoThreshold("Default dark no-reset");
			run("Threshold...");
			run("Convert to Mask");
			run("Fill Holes");
			
			//save image
			name = replace(list[i], ".tif", "");
        	saveAs("Tiff", output + name + "_mask.tif");
			run("Close All");
			}
