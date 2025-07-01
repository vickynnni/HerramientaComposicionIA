import os
import cv2
from utils.metrics import calculate_psnr, calculate_ssim

# Sample script to calculate PSNR and SSIM metrics from saved images in two directories
# using calculate_psnr and calculate_ssim functions from: https://github.com/JingyunLiang/SwinIR
# modificada para resize imagenes automaticamente

gt_path = '/home/jovyan/pruebas/data/test/gt/'
results_path = '/home/jovyan/pruebas/results/images/MSE_502/Scores/scores/'

imgsName = sorted(os.listdir(results_path))
gtsName = sorted(os.listdir(gt_path))
# print(imgsName)
# print(gtsName)

assert len(imgsName) == len(gtsName)

cumulative_psnr, cumulative_ssim = 0, 0
for i in range(1, len(imgsName)):
    print('Processing image: %s' % (imgsName[i]))
    res = cv2.imread(os.path.join(results_path, imgsName[i]), cv2.IMREAD_COLOR)
    gt = cv2.imread(os.path.join(gt_path, gtsName[i]), cv2.IMREAD_COLOR)
    print(os.path.join(results_path, imgsName[i]))
    
    if res.shape != gt.shape:
        print(f"Resizing {imgsName[i]} ({res.shape}) to match {gtsName[i]} ({gt.shape})")
        res = cv2.resize(res, (gt.shape[1], gt.shape[0]), interpolation=cv2.INTER_AREA)
    
    cur_psnr = calculate_psnr(res, gt, test_y_channel=True)
    cur_ssim = calculate_ssim(res, gt, test_y_channel=True)
    print('PSNR is %.4f and SSIM is %.4f' % (cur_psnr, cur_ssim))
    cumulative_psnr += cur_psnr
    cumulative_ssim += cur_ssim
print('Testing set, PSNR is %.4f and SSIM is %.4f' % (cumulative_psnr / len(imgsName), cumulative_ssim / len(imgsName)))
print(results_path)
