import os
from os import listdir
from os.path import isfile
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
        self.transforms = torchvision.transforms.Compose([torchvision.transforms.ToTensor()])

    def get_loaders(self, parse_patches=True, validation='scores'):
        print("=> evaluating scores test set...")
        current_directory = os.getcwd()

        # Print the current working directory
        print("Current working directory:", current_directory)
        train_dataset = ScoresDataset(dir=os.path.join(self.config.data.data_dir,'data', 'train'),
                                        n=self.config.training.patch_n,
                                        patch_size=self.config.data.image_size,
                                        transforms=self.transforms,
                                        filelist=None,
                                        parse_patches=parse_patches)
        val_dataset = ScoresDataset(dir=os.path.join(self.config.data.data_dir, 'data', 'test'),
                                      n=self.config.training.patch_n,
                                      patch_size=self.config.data.image_size,
                                      transforms=self.transforms,
                                      filelist='scorestest.txt',
                                      parse_patches=parse_patches)

        if not parse_patches:
            self.config.training.batch_size = 1
            self.config.sampling.batch_size = 1

        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=self.config.training.batch_size,
                                                   shuffle=True, num_workers=self.config.data.num_workers,
                                                   pin_memory=True)
        val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=self.config.sampling.batch_size,
                                                 shuffle=False, num_workers=self.config.data.num_workers,
                                                 pin_memory=True)

        return train_loader, val_loader


class ScoresDataset(torch.utils.data.Dataset):
    def __init__(self, dir, patch_size, n, transforms, filelist=None, parse_patches=True):
        super().__init__()

        if filelist is None:
            scores_dir = dir
            input_names, gt_names = [], []

            # Update paths for clean and rain images

            clean_dir = os.path.join('/home/jovyan/pruebas/','data', 'test', '1-B')  # Folder for clean images
            rain_dir = os.path.join('/home/jovyan/pruebas/','data', 'train', '1-A')   # Folder for rain images

           
            # clean_dir = os.path.join('/home/jovyan/WeatherDiffusion','data', 'test', '1-B')  # Folder for clean images
            # rain_dir = os.path.join('/home/jovyan/WeatherDiffusion','data', 'train', '1-A')   # Folder for rain images
            #print("Files in clean images directory:", listdir(clean_dir))
            #print("Files in rain images directory:", listdir(rain_dir))
            
            # List all files in the clean directory
            clean_images = [f for f in listdir(clean_dir) if isfile(os.path.join(clean_dir, f))]
            print(f"Files in clean images directory: {len(clean_images)}")
            print({clean_dir})
            assert len(clean_images) == 3736 #1895 #32 # 3736  # Adjust according to your dataset
            
            # Pair clean and rain images by the same filename
            for image in clean_images:
                # Use the same filename to get the corresponding rain image
                rain_image_path = os.path.join(rain_dir, image)
                if os.path.isfile(rain_image_path):
                    input_names.append(rain_image_path)  # Path for rain image
                    gt_names.append(os.path.join(clean_dir, image))  # Path for clean image

            print(len(input_names))  # Check the number of images processed

            x = list(enumerate(input_names))
            random.shuffle(x)
            indices, input_names = zip(*x)
            gt_names = [gt_names[idx] for idx in indices]
            self.dir = None
        else:
            self.dir = dir
            train_list = os.path.join(dir, filelist)
            with open(train_list) as f:
                contents = f.readlines()
                input_names = [i.strip() for i in contents]
                gt_names = [i.strip().replace('input', 'gt') for i in input_names]

        self.input_names = input_names
        self.gt_names = gt_names
        self.patch_size = patch_size
        self.transforms = transforms
        self.n = n
        self.parse_patches = parse_patches

    @staticmethod
    def get_params(img, output_size, n):
        w, h = img.size
        th, tw = output_size
        if w == tw and h == th:
            return 0, 0, h, w

        i_list = [random.randint(0, h - th) for _ in range(n)]
        j_list = [random.randint(0, w - tw) for _ in range(n)]
        return i_list, j_list, th, tw

    @staticmethod
    def n_random_crops(img, x, y, h, w):
        crops = []
        for i in range(len(x)):
            new_crop = img.crop((y[i], x[i], y[i] + w, x[i] + h))
            crops.append(new_crop)
        return tuple(crops)

    def get_images(self, index):
        input_name = self.input_names[index]
        gt_name = self.gt_names[index]
        img_id = re.split('/', input_name)[-1][:-4]

        input_img = PIL.Image.open(os.path.join(self.dir, input_name)).convert('RGB') if self.dir else PIL.Image.open(input_name).convert('RGB')

        #print(f"Image mode: {input_img.mode}")
        
        #input_img = input_img.convert('RGB') # new by vicky
        try:
            gt_img = PIL.Image.open(os.path.join(self.dir, gt_name)).convert('RGB') if self.dir else PIL.Image.open(gt_name).convert('RGB')
        except:
            gt_img = PIL.Image.open(os.path.join(self.dir, gt_name)).convert('RGB') if self.dir else \
                PIL.Image.open(gt_name).convert('RGB')

        if self.parse_patches:
            i, j, h, w = self.get_params(input_img, (self.patch_size, self.patch_size), self.n)
            #print("Type of input_img:", type(input_img))
            input_img = self.n_random_crops(input_img, i, j, h, w)
            gt_img = self.n_random_crops(gt_img, i, j, h, w)
            outputs = [torch.cat([self.transforms(input_img[i]), self.transforms(gt_img[i])], dim=0)
                       for i in range(self.n)]
            return torch.stack(outputs, dim=0), img_id
        else:
            # Resizing images to multiples of 16 for whole-image restoration
            wd_new, ht_new = input_img.size
            if ht_new > wd_new and ht_new > 1024:
                wd_new = int(np.ceil(wd_new * 1024 / ht_new))
                ht_new = 1024
            elif ht_new <= wd_new and wd_new > 1024:
                ht_new = int(np.ceil(ht_new * 1024 / wd_new))
                wd_new = 1024
            wd_new = int(16 * np.ceil(wd_new / 16.0))
            ht_new = int(16 * np.ceil(ht_new / 16.0))
            input_img = input_img.resize((wd_new, ht_new), PIL.Image.LANCZOS)
            gt_img = gt_img.resize((wd_new, ht_new), PIL.Image.LANCZOS)

            return torch.cat([self.transforms(input_img), self.transforms(gt_img)], dim=0), img_id

    def __getitem__(self, index):
        res = self.get_images(index)
        return res

    def __len__(self):
        return len(self.input_names)
