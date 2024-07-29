import os.path as osp

import numpy as np
import PIL.Image


def lblsave(filename, lbl):
    import imgviz

    if osp.splitext(filename)[1] != ".png":
        filename += ".png"
    # Assume label ranses [-1, 254] for int32,
    # and [0, 255] for uint8 as VOC.
    if lbl.min() >= -1 and lbl.max() < 255:
        lbl_pil = PIL.Image.fromarray(lbl.astype(np.uint8), mode="P")
        colormap = imgviz.label_colormap()
        lbl_pil.putpalette(colormap.flatten())
        lbl_pil.save(filename)
    else:
        raise ValueError(
            "[%s] Cannot save the pixel-wise class label as PNG. "
            "Please consider using the .npy format." % filename
        )


def lblsave_old(filename, lbl, names, class_rgb, segmentation_class):
    here = osp.dirname(osp.abspath(__file__))

    if osp.splitext(filename)[1] != '.png':
        filename += '.png'
    if lbl.min() >= -1 and lbl.max() < 255:
        lbl_pil = PIL.Image.fromarray(lbl.astype(np.uint8), mode='P')
        colormap = np.ones((255, 3), dtype=float)
        colormap[0] = [0, 0, 0]
        for num_classes, classes in enumerate(names):
            color_val = class_rgb[segmentation_class.index(classes)]

            for i in range(3):
                color_val[i] = 256 - color_val[i]
                colormap[num_classes+1] = color_val
        lbl_pil.putpalette((colormap * 255).astype(np.uint8).flatten())
        lbl_pil.save(filename)

    else:
        raise ValueError(
            '[%s] Cannot save the pixel-wise class label as PNG. '
            'Please consider using the .npy format.' % filename
        )
