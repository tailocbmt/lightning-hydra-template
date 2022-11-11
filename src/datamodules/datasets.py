import os
import pandas as pd

import torch
import torchvision.transforms as transform
from torch.utils.data import DataLoader
from torch.utils.data import Dataset
import torch.nn.functional as F
from PIL import Image


class VSDataset:
    @classmethod
    def initialize(cls, img_size, datapath, imagenet_norm=False):
        cls.datasets = {
            'deepfashion': DatasetDeepFashion,
        }

        if imagenet_norm:
            cls.img_mean = [0.485, 0.456, 0.406]
            cls.img_std = [0.229, 0.224, 0.225]
        else:
            cls.img_mean = [0.5, 0.5, 0.5]
            cls.img_std = [0.5, 0.5, 0.5]
        print(f'Use norm img_mean {cls.img_mean}\timg_std {cls.img_std}')
        
        cls.img_size = img_size 
        cls.datapath = datapath
    
    @classmethod
    def build_dataloader(cls, benchmark, bsz, nworker, split):
        nworker = nworker if split == 'train' else 0 
        shuffle = False
        if split == 'train':
            shuffle = True
            transforms = transform.Compose([
                transform.Resize(size=(cls.img_size, cls.img_size)),
                transform.RandomHorizontalFlip(p=.5),
                transform.ToTensor(),
                transform.Normalize(cls.img_mean, cls.img_std)
                ])
        else:
            transforms = transform.Compose([
                transform.Resize(size=(cls.img_size, cls.img_size)),
                transform.ToTensor(),
                transform.Normalize(cls.img_mean, cls.img_std)
                ])

        dataset = cls.datasets[benchmark](cls.datapath, transforms=transforms, split=split)
        dataloader = DataLoader(dataset, batch_size=bsz, shuffle=shuffle, num_workers=nworker, pin_memory=True)

        return dataloader


class DatasetDeepFashion(Dataset):
    def __init__(self, datapath, transforms, split):
        self.split = 'val' if split in ['val', 'test'] else 'train'
        self.datapath = datapath
        self.img_path = os.path.join(self.datapath, self.split, 'image')
        self.transforms = transforms
        self.img_metadata = self.build_img_metadata()
    
    def __len__(self):
        return len(self.img_metadata['image_name'])

    def __getitem__(self, idx):
        #TODO: check this if data per batch is not loaded correctly
        triplet_paths, triplet_boxes, triplet_ids = self.sample(idx)
        triplet_imgs = self.load_frames(triplet_paths, boxes=triplet_boxes)
        # print("after load frames")
        # len(triplet_imgs)= 3 ; type(triplet_imgs) = list
        # type(triplet_imgs[0])=PIL Image
        triplet_imgs = [self.transforms(imgs) for imgs in triplet_imgs]
        # print(triplet_imgs[0].shape=(3, 224, 224))

        # batch = {
            # 'images': triplet_imgs, # list(torch.tensor(3, 224, 224)*3)
            # 'ids': triplet_ids, # nd.array([np.int64, np.int64, np.int64])
        # }
        return triplet_imgs, triplet_ids
        
    def load_frames(self, paths, boxes=None):
        # load images from paths
        # if boxes, crop corresponding box (x1,y1,x2,y2) from image
        frames = []
        for path, box in zip(paths, boxes):
            frames.append(self.read_image(path, box=box))
        return frames 
    
    def read_image(self, image_name, box=None):
        r"""Return RGB image in PIL Image"""
        image = Image.open(os.path.join(self.img_path, image_name))
        if box is not None:
            image = image.crop(box)
        return image.convert('RGB')

    def sample(self, idx):
        """Sample path of triplet of images from the dataset"""
        # a_path, p_path, n_path = self.img_metadata['image_name'].iloc[idx].values
        paths = self.img_metadata['image_name'].iloc[idx].values
        # a_box, p_box, n_box = [self.img_metadata['box'].iloc[idx].values for _ in range(3)]
        boxes = self.img_metadata['box'].iloc[idx].values.reshape((3, -1))
        ids = self.img_metadata['category_id'].iloc[idx].values
        return paths, boxes, ids

    def build_class_ids(self):
        """Build a dictionary of class ids"""
        class_ids = {}
        for i, class_name in enumerate(self.df['class_name'].unique()):
            class_ids[class_name] = i
        return class_ids
    
    def build_img_metadata(self):

        def read_metadata(df):
            """ Return metadata
            metadata: Dictionary
                image_name
                box
                category_id    
            """
            metadata = {
                'image_name': df[[
                    'image_name_a', 
                    'image_name_p', 
                    'image_name_n']],
                'box': df [[
                    'x_1_a', 'y_1_a', 'x_2_a', 'y_2_a',
                    'x_1_p', 'y_1_p', 'x_2_p', 'y_2_p',
                    'x_1_n', 'y_1_n', 'x_2_n', 'y_2_n']],
                'category_id': df[[
                    'category_id_a',
                    'category_id_p',
                    'category_id_n']]
            }
            return metadata
        
        def load_csv(split):
            with open(os.path.join(self.datapath, split + '_triplets_small.csv'), 'r') as f:
                df = pd.read_csv(f)
                return df
                
        df = load_csv(self.split)

        img_metadata = {}
        if self.split in ['train', 'val']:
            img_metadata.update(read_metadata(df))
        else:
            raise Exception('Undefined split %s: ' %self.split)
        
        print('Total (%s) images are: %d' %(self.split, len(img_metadata['image_name'])))
        return img_metadata
    