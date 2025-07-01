import os
from os import listdir
from os.path import isfile, join
import torch
import numpy as np
import torchvision
import torch.utils.data
import PIL
import re
import random

class Scores:
    def __init__(self, config):
        self.config = config
        self.transforms = torchvision.transforms.Compose([
            torchvision.transforms.ToTensor()
        ])

    def get_loaders(self, parse_patches=True, validation='scores'):
        print(f"=> Using dataset: {self.config.data.dataset}") # Use dataset name from config

        train_dir = join(self.config.data.data_dir, 'data', 'train')
        test_dir = join(self.config.data.data_dir, 'data', 'test')
        test_filelist = 'scorestest.txt'

        print(f"Train directory: {train_dir}")
        print(f"Test directory: {test_dir}")
        print(f"Test filelist: {test_filelist}")

        train_dataset = ScoresDataset(
            dir=train_dir,
            patch_size=self.config.data.image_size,
            n=self.config.training.patch_n,
            transforms=self.transforms,
            filelist=None,
            parse_patches=parse_patches
        )

        val_dataset = ScoresDataset(
            dir=test_dir,
            patch_size=self.config.data.image_size,
            n=self.config.training.patch_n,
            transforms=self.transforms,
            filelist=test_filelist,
            parse_patches=parse_patches
        )

        train_batch_size = self.config.training.batch_size
        val_batch_size = self.config.sampling.batch_size
        if not parse_patches:
            val_batch_size = 1

        train_loader = torch.utils.data.DataLoader(
            train_dataset,
            batch_size=train_batch_size,
            shuffle=True,
            num_workers=self.config.data.num_workers,
            pin_memory=True,
            drop_last=True
        )

        val_loader = torch.utils.data.DataLoader(
            val_dataset,
            batch_size=val_batch_size,
            shuffle=False,
            num_workers=self.config.data.num_workers,
            pin_memory=True
        )

        return train_loader, val_loader

class ScoresDataset(torch.utils.data.Dataset):
    """
    Dataset class for loading paired input/ground_truth data
    (e.g., noisy/clean spectrograms or images).
    Expects the following directory structure:
    - dir/train/input/
    - dir/train/gt/
    - dir/test/input/
    - dir/test/gt/
    - dir/test/scorestest.txt
    """
    def __init__(self, dir, patch_size, n, transforms, filelist=None, parse_patches=True):
        super().__init__()

        self.dir = dir # Store base directory (train or test)
        self.patch_size = patch_size
        self.n_patches_per_image = n
        self.transforms = transforms
        self.parse_patches = parse_patches
        self.input_names = []
        self.gt_names = []

        if filelist is None:
            print(f"Initializing training dataset from: {self.dir}")
            input_dir = join(self.dir, 'input')
            gt_dir = join(self.dir, 'gt')

            if not os.path.isdir(input_dir):
                raise FileNotFoundError(f"Input directory not found: {input_dir}")
            if not os.path.isdir(gt_dir):
                raise FileNotFoundError(f"Ground truth directory not found: {gt_dir}")

            image_filenames = [f for f in listdir(input_dir) if isfile(join(input_dir, f))]
            print(f"Found {len(image_filenames)} potential files in {input_dir}")

            paired_count = 0
            for filename in image_filenames:
                input_path = join(input_dir, filename)
                gt_path = join(gt_dir, filename)

                if isfile(input_path) and isfile(gt_path):
                    self.input_names.append(input_path)
                    self.gt_names.append(gt_path)
                    paired_count += 1
                else:
                    if not isfile(gt_path):
                         print(f"Warning: Missing corresponding ground truth file for {filename} in {gt_dir}")

            print(f"Successfully paired {paired_count} input/gt files for training.")

            if not self.input_names:
                 raise ValueError(f"No paired input/gt files found in {input_dir} and {gt_dir}. Check directory structure and filenames.")

            # Shuffle the lists together
            temp_list = list(zip(self.input_names, self.gt_names))
            random.shuffle(temp_list)
            self.input_names, self.gt_names = zip(*temp_list)
            self.dir = None 

        else:
            # --- Load Test/Validation Data ---
            test_list_path = join(self.dir, filelist)
            print(f"Initializing test/validation dataset from list: {test_list_path}")

            if not isfile(test_list_path):
                raise FileNotFoundError(f"Test file list not found: {test_list_path}")

            with open(test_list_path) as f:
                # Read relative paths from the file (expecting format like 'input/image.png')
                relative_input_paths = [line.strip() for line in f if line.strip()]

            print(f"Found {len(relative_input_paths)} entries in {filelist}")

            paired_count = 0
            for rel_input_path in relative_input_paths:
                input_path = join(self.dir, rel_input_path)

                if 'input' not in rel_input_path:
                     print(f"Warning: Cannot derive GT path from '{rel_input_path}'. Expecting 'input' folder in path.")
                     continue

                rel_gt_path = rel_input_path.replace('input', 'gt', 1)
                gt_path = join(self.dir, rel_gt_path)

                if isfile(input_path) and isfile(gt_path):
                    self.input_names.append(rel_input_path)
                    self.gt_names.append(rel_gt_path)
                    paired_count += 1
                else:
                    print(f"Warning: Missing file pair for list entry '{rel_input_path}'. Checked {input_path} and {gt_path}")

            print(f"Successfully paired {paired_count} input/gt files for validation/testing.")
            if not self.input_names:
                 raise ValueError(f"No valid, paired input/gt files found based on {test_list_path}. Check file list paths and file existence.")

    @staticmethod
    def get_params(img_size, output_size, n):
        w, h = img_size
        th, tw = output_size
        if w < tw or h < th:
             raise ValueError(f"Image size ({w}x{h}) is smaller than patch size ({tw}x{th})")

        i_list = [random.randint(0, h - th) for _ in range(n)]
        j_list = [random.randint(0, w - tw) for _ in range(n)]
        return i_list, j_list, th, tw

    @staticmethod
    def n_random_crops(img, x_coords, y_coords, crop_h, crop_w):
        crops = []
        for i in range(len(x_coords)):
            left = y_coords[i]
            top = x_coords[i]
            right = left + crop_w
            bottom = top + crop_h
            new_crop = img.crop((left, top, right, bottom))
            crops.append(new_crop)
        return crops if len(crops) > 1 else crops[0]

    def get_images(self, index):
        input_name = self.input_names[index]
        gt_name = self.gt_names[index]

        input_path = join(self.dir, input_name) if self.dir else input_name
        gt_path = join(self.dir, gt_name) if self.dir else gt_name

        img_id = os.path.splitext(os.path.basename(input_name))[0]

        try:
            input_img = PIL.Image.open(input_path).convert('RGB')
            gt_img = PIL.Image.open(gt_path).convert('RGB')
        except FileNotFoundError as e:
            print(f"Error loading image: {e}")
            raise e
        except Exception as e:
            print(f"Error processing images {input_path} or {gt_path}: {e}")
            raise e


        if self.parse_patches:
            i, j, h, w = self.get_params(input_img.size, (self.patch_size, self.patch_size), self.n_patches_per_image)
            input_crops = self.n_random_crops(input_img, i, j, h, w)
            gt_crops = self.n_random_crops(gt_img, i, j, h, w)

            if isinstance(input_crops, list):
                 outputs = [torch.cat([self.transforms(in_crop), self.transforms(gt_crop)], dim=0)
                           for in_crop, gt_crop in zip(input_crops, gt_crops)]
                 return torch.stack(outputs, dim=0), img_id 
            else:
                 return torch.cat([self.transforms(input_crops), self.transforms(gt_crops)], dim=0), img_id

        else:
            wd_new, ht_new = input_img.size
            if wd_new % 16 != 0:
                 wd_new = int(16 * np.ceil(wd_new / 16.0))
            if ht_new % 16 != 0:
                 ht_new = int(16 * np.ceil(ht_new / 16.0))

            if (wd_new, ht_new) != input_img.size:
                 input_img = input_img.resize((wd_new, ht_new), PIL.Image.LANCZOS)
                 gt_img = gt_img.resize((wd_new, ht_new), PIL.Image.LANCZOS)

            return torch.cat([self.transforms(input_img), self.transforms(gt_img)], dim=0), img_id

    def __getitem__(self, index):
        return self.get_images(index)

    def __len__(self):
        return len(self.input_names)
