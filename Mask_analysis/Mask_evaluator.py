import os
import re
import numpy as np
import pandas as pd
from skimage import io, transform as skt


class MaskTrackEvaluator:
    """
    Evaluates predicted ROI masks vs. ground-truth masks and associated track CSVs.
    """

    def __init__(self, roi_dir, gt_dir, track_dir, nm_per_pixel=117):
        self.roi_dir = roi_dir
        self.gt_dir = gt_dir
        self.track_dir = track_dir
        self.nm_per_pixel = nm_per_pixel

        # --- Step 1: Collect and align filenames ---
        self.roi_files = self._list_images(roi_dir)
        self.gt_files = self._list_images(gt_dir)
        self.track_files = self._list_tracks(track_dir)

        # Match files by numeric identifiers
        self.file_triplets = self._align_files()
        if not self.file_triplets:
            raise ValueError("No aligned ROI / GT / Track files found!")

        # --- Step 2: Load all masks and track data ---
        self.data = []
        for num, roi_name, gt_name, track_name in self.file_triplets:
            roi_mask = self._read_mask(os.path.join(roi_dir, roi_name))
            gt_mask = self._read_gt(os.path.join(gt_dir, gt_name))
            df_tracks = self._load_tracks(os.path.join(track_dir, track_name))
            self.data.append({
                "file_number": num,
                "roi_file": roi_name,
                "gt_file": gt_name,
                "track_file": track_name,
                "roi_mask": roi_mask,
                "gt_mask": gt_mask,
                "tracks": df_tracks
            })
        print(f"✅ Loaded {len(self.data)} aligned sets.")

    # -----------------------------------------------------
    #                FILE AND IO HELPERS
    # -----------------------------------------------------

    def _extract_number(self, filename):
        nums = re.findall(r'\d+', filename)
        return int(nums[-1]) if nums else -1

    def _list_images(self, folder):
        exts = {'.tif', '.tiff', '.png', '.jpg', '.jpeg', '.bmp'}
        files = [f for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in exts]
        return sorted(files, key=self._extract_number)

    def _list_tracks(self, folder):
        files = [f for f in os.listdir(folder) if f.lower().endswith('.csv')]
        return sorted(files, key=self._extract_number)

    def _align_files(self):
        """
        Aligns ROI, GT, and track files based on their numeric suffix.
        Returns a list of tuples: (number, roi_filename, gt_filename, track_filename)
        """
        roi_map = {self._extract_number(f): f for f in self.roi_files}
        gt_map = {self._extract_number(f): f for f in self.gt_files}
        track_map = {self._extract_number(f): f for f in self.track_files}

        aligned = []
        for num in sorted(set(roi_map) & set(gt_map) & set(track_map)):
            aligned.append((num, roi_map[num], gt_map[num], track_map[num]))

        # Report mismatches
        all_nums = set(roi_map) | set(gt_map) | set(track_map)
        missing = all_nums - set(num for num, *_ in aligned)
        if missing:
            print(f"⚠️ Missing sets for numbers: {sorted(missing)}")

        return aligned

    def _read_mask(self, path):
        img = io.imread(path)
        if img.ndim == 3:
            img = img[..., 0]
        return (img > 0).astype(np.uint8)

    def _read_gt(self, path):
        mask = self._read_mask(path)
        if mask.shape == (428, 428):
            return mask
        h, w = mask.shape
        if h >= 428 and w >= 428:
            sh, sw = (h - 428) // 2, (w - 428) // 2
            return mask[sh:sh + 428, sw:sw + 428].astype(np.uint8)
        resized = skt.resize(mask, (428, 428), order=0, preserve_range=True, anti_aliasing=False)
        return (resized > 0.5).astype(np.uint8)

    def _load_tracks(self, path):
        df = pd.read_csv(path)
        df[' X (px)'] = (df[' X (nm)'] / self.nm_per_pixel).round().astype(int)
        df['Y (px)'] = (df['Y (nm)'] / self.nm_per_pixel).round().astype(int)
        return df

    # -----------------------------------------------------
    #                    METRICS
    # -----------------------------------------------------

    def jaccard_index(self, a, b):
        inter = np.logical_and(a, b).sum()
        union = np.logical_or(a, b).sum()
        return 1.0 if union == 0 else inter / union

    def dice_coefficient(self, a, b):
        inter = np.logical_and(a, b).sum()
        denom = (a.sum() + b.sum())
        return 1.0 if denom == 0 else 2 * inter / denom

    # -----------------------------------------------------
    #             EVALUATION FUNCTIONS
    # -----------------------------------------------------

    def evaluate_mask_metrics(self):
        """Computes Dice, Jaccard, etc. for each aligned set."""
        rows = []
        for entry in self.data:
            roi = entry["roi_mask"]
            gt = entry["gt_mask"]
            jaccard = self.jaccard_index(roi, gt)
            dice = self.dice_coefficient(roi, gt)
            inter = int(np.logical_and(roi, gt).sum())
            false_pos = int((roi.sum() - inter))
            rows.append({
                "File Number": entry["file_number"],
                "ROI File": entry["roi_file"],
                "GT File": entry["gt_file"],
                "Jaccard Index": jaccard,
                "Dice Coefficient": dice,
                "Intersection": inter,
                "False Positives": false_pos
            })
        return pd.DataFrame(rows)

    def find_track_ids_in_mask(self, mask, df_tracks):
        y_idx, x_idx = np.where(mask == 1)
        coords = set(zip(x_idx, y_idx))
        ids = set()
        for _, row in df_tracks.iterrows():
            coord = (int(row[' X (px)']), int(row['Y (px)']))
            if coord in coords:
                ids.add(int(row['Track ID']))
        return ids

    def evaluate_track_comparison(self):
        """Finds extra or missing track IDs between predicted and GT masks using only first frame coordinates."""
        rows = []
        for entry in self.data:
            # Get only Frame=1 coordinates
            df = entry["tracks"]
            first_frame_tracks = df[df['Frame'] == 1]
            
            # Find track IDs in masks using only first frame positions
            pred_ids = self.find_track_ids_in_mask(entry["roi_mask"], first_frame_tracks)
            gt_ids = self.find_track_ids_in_mask(entry["gt_mask"], first_frame_tracks)
            
            # Compare track sets
            extra = sorted(list(pred_ids - gt_ids))
            lost = sorted(list(gt_ids - pred_ids))
            
            rows.append({
                "File Number": entry["file_number"],
                "ROI File": entry["roi_file"],
                "GT File": entry["gt_file"], 
                "Track File": entry["track_file"],
                "Num Extra": len(extra),
                "Num Lost": len(lost),
                "Extra Track IDs": ",".join(map(str, extra)) if extra else "",
                "Lost Track IDs": ",".join(map(str, lost)) if lost else ""
            })
        return pd.DataFrame(rows)
    # -----------------------------------------------------
    #                 AGGREGATION / OUTPUT
    # -----------------------------------------------------

    def summarize_results(self, df, label="Overall Average"):
        """Adds an average row for all numeric columns."""
        numeric_cols = df.select_dtypes(include=np.number).columns
        summary = df[numeric_cols].mean().to_dict()
        summary["File Number"] = label
        return pd.concat([df, pd.DataFrame([summary])], ignore_index=True)



    def save_results(self, excel_filename="evaluation_results.xlsx", track_comparison=False):
        """Saves the evaluation results to an Excel workbook."""

        with pd.ExcelWriter(excel_filename) as writer:
            df_metrics = self.summarize_results(self.evaluate_mask_metrics())
            df_metrics.to_excel(writer, sheet_name="Mask Metrics", index=False)
            if track_comparison:
                df_tracks = self.summarize_results(self.evaluate_track_comparison())
                df_tracks.to_excel(writer, sheet_name="Track Comparison", index=False)
        print(f"💾 Saved results to {excel_filename}")


#Example usage:

# Define directories:

roi_pred_masks_dir = r
gt_dir = r
track_dir = r


Ilastik_evaluator_FL = MaskTrackEvaluator(roi_dir=roi_dir_Ilastik_FL, gt_dir=gt_dir_FL, track_dir=track_dir_FL)
Ilastik_evaluator_FL.save_results("Ilastik_evaluation_results_FL_Final.xlsx", track_comparison=True)

