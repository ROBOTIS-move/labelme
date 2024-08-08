import io
import math
import os.path as osp

import numpy as np
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont


def shape_to_mask(img_shape, points, shape_type=None,
                  line_width=10, point_size=5):
    mask = np.zeros(img_shape[:2], dtype=np.uint8)
    mask = PIL.Image.fromarray(mask)
    draw = PIL.ImageDraw.Draw(mask)
    xy = [tuple(point) for point in points]
    if shape_type == 'circle':
        assert len(xy) == 2, 'Shape of shape_type=circle must have 2 points'
        (cx, cy), (px, py) = xy
        d = math.sqrt((cx - px) ** 2 + (cy - py) ** 2)
        draw.ellipse([cx - d, cy - d, cx + d, cy + d], outline=1, fill=1)
    elif shape_type == 'rectangle':
        assert len(xy) == 2, 'Shape of shape_type=rectangle must have 2 points'
        draw.rectangle(xy, outline=1, fill=1)
    elif shape_type == '3D-Box':
        assert len(xy) == 2, 'Shape of shape_type=3D-Box must have 2 points'
        draw.rectangle(xy, outline=1, fill=1)
    elif shape_type == 'line':
        assert len(xy) == 2, 'Shape of shape_type=line must have 2 points'
        draw.line(xy=xy, fill=1, width=line_width)
    elif shape_type == 'linestrip':
        draw.line(xy=xy, fill=1, width=line_width)
    elif shape_type == 'point':
        assert len(xy) == 1, 'Shape of shape_type=point must have 1 points'
        cx, cy = xy[0]
        r = point_size
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=1, fill=1)
    else:
        # assert len(xy) > 2, 'Polygon must have points more than 2'
        if len(xy) > 2:
            draw.polygon(xy=xy, outline=1, fill=1)

    mask = np.array(mask, dtype=bool)
    return mask


def getClsId(label, names, seg_class, file_name=''):
    if label in seg_class:
        if len(names) == 0:
            cls_id = 1
            names.append(label)
        else:
            if label not in names:
                names.append(label)
                cls_id = len(names)
                # print("get new class")
            else:
                cls_id = names.index(label) + 1

    else:
        print('\033[31m' "[{}] There is no class name: {}".format(file_name, label) + '\033[0m')
        cls_id = 0
        names = None
    return cls_id, names


def shapes_to_label(img_shape, shapes, label_name_to_value, seg_class, type='class', file_name=''):
    assert type in ['class', 'instance']
    cls = np.zeros(img_shape[:2], dtype=np.int32)
    if type == 'instance':
        ins = np.zeros(img_shape[:2], dtype=np.int32)
        instance_names = ['_background_']
    names = []
    for shape in shapes:
        points = shape['points']
        label = shape['label']
        shape_type = shape.get('shape_type', None)
        class_names = []
        if type == 'class':
            cls_name = label
            # print(cls_name)
        elif type == 'instance':
            cls_name = label.split('-')[0]
            if label not in instance_names:
                instance_names.append(label)
            ins_id = instance_names.index(label)

        cls_id, names = getClsId(label, names, seg_class, file_name)

        if names is None:
            return None, None
        else:
            mask = shape_to_mask(img_shape[:2], points, shape_type)
            cls[mask] = cls_id
            if type == 'instance':
                ins[mask] = ins_id
    if type == 'instance':
        return cls, ins
    return cls, names


def label_colormap(N=256):

    def bitget(byteval, idx):
        return ((byteval & (1 << idx)) != 0)

    cmap = np.zeros((N, 3))
    for i in range(0, N):
        id = i
        r, g, b = 0, 0, 0
        for j in range(0, 8):
            r = np.bitwise_or(r, (bitget(id, 0) << 7 - j))
            g = np.bitwise_or(g, (bitget(id, 1) << 7 - j))
            b = np.bitwise_or(b, (bitget(id, 2) << 7 - j))
            id = (id >> 3)
        cmap[i, 0] = r
        cmap[i, 1] = g
        cmap[i, 2] = b
    cmap = cmap.astype(np.float32) / 255

    return cmap


def _validate_colormap(colormap, n_labels):

    if colormap is None:
        colormap = label_colormap(n_labels)
    else:
        assert colormap.shape == (colormap.shape[0], 3), \
            'colormap must be sequence of RGB values'
        assert 0 <= colormap.min() and colormap.max() <= 1, \
            'colormap must ranges 0 to 1'
    return colormap


# similar function as skimage.color.label2rgb
def label2rgb(
    lbl, img=None, n_labels=None, alpha=0.5, thresh_suppress=0, colormap=None,
):
    if n_labels is None:
        n_labels = len(np.unique(lbl))
    # print("n_labels:", n_labels)
    colormap = _validate_colormap(colormap, n_labels)

    colormap = (colormap * 255)
    # print("color map:", len(colormap))
    # print("lbl", list(lbl[1000]))
    # print("test :", colormap)
    lbl_viz = colormap[lbl]

    # print("lbl_viz :", lbl_viz)
    lbl_viz[lbl == -1] = (0, 0, 0)  # unlabeled
    # lbl_viz[lbl == 1] = (68, 68, 128)
    if img is not None:
        img_gray = PIL.Image.fromarray(img).convert('LA')
        img_gray = np.asarray(img_gray.convert('RGB'))
        # img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        # img_gray = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2RGB)
        lbl_viz = alpha * lbl_viz + (1 - alpha) * img_gray
        lbl_viz = lbl_viz.astype(np.uint8)

    return lbl_viz


def draw_label(
        label,
        img=None,
        label_names=None,
        names=None,
        class_rgb=None,
        segmentation_class=None,
        colormap=None,
        **kwargs):
    """Draw pixel-wise label with colorization and label names.

    label: ndarray, (H, W)
        Pixel-wise labels to colorize.
    img: ndarray, (H, W, 3), optional
        Image on which the colorized label will be drawn.
    label_names: iterable
        List of label names.
    """
    import matplotlib.pyplot as plt

    if label_names is None:
        label_names = [str(l) for l in range(label.max() + 1)]

    colormap = _validate_colormap(colormap, len(label_names))

    class_rgb = np.array(class_rgb, np.uint8)

    for index, labels in enumerate(names):
        colormap[index+1] = class_rgb[segmentation_class.index(labels)]/255.0

    label_viz = label2rgb(
        label, img, n_labels=len(label_names), colormap=colormap, **kwargs
    )
    plt.imshow(label_viz)
    plt.axis('off')

    plt_handlers = []
    plt_titles = []
    # print (label_names)
    for label_value, label_name in enumerate(label_names):
        if label_value not in label:
            continue
        fc = colormap[label_value]
        p = plt.Rectangle((0, 0), 1, 1, fc=fc)
        plt_handlers.append(p)
        plt_titles.append('{value}: {name}'
                          .format(value=label_value, name=label_name))
    # plt.legend(plt_handlers, plt_titles, loc='lower right', framealpha=.5)

    f = io.BytesIO()
    plt.savefig(f, bbox_inches='tight', pad_inches=0)
    # plt.cla()
    # plt.close()

    # plt.switch_backend(backend_org)

    out_size = (label_viz.shape[1], label_viz.shape[0])
    out = PIL.Image.open(f).resize(out_size, PIL.Image.BILINEAR).convert('RGB')
    out = np.asarray(out)
    return out


def draw_instances(
    image=None,
    bboxes=None,
    labels=None,
    masks=None,
    captions=None,
):
    import matplotlib

    # TODO(wkentaro)
    assert image is not None
    assert bboxes is not None
    assert labels is not None
    assert masks is None
    assert captions is not None
    font_size = 20
    viz = PIL.Image.fromarray(image)
    draw = PIL.ImageDraw.ImageDraw(viz)

    font_path = osp.join(
        osp.dirname(matplotlib.__file__),
        'mpl-data/fonts/ttf/DejaVuSans.ttf'
    )
    font = PIL.ImageFont.truetype(font_path, font_size)

    colormap = label_colormap(255)

    for bbox, label, caption in zip(bboxes, labels, captions):
        color = colormap[label]
        color = tuple((color * 255).astype(np.uint8).tolist())

        xmin, ymin, xmax, ymax = bbox
        draw.line(
            [
                (xmin, ymin),
                (xmin, ymax),
                (xmax, ymax),
                (xmax, ymin),
                (xmin, ymin)
            ],
            width=5,
            fill=color)
        # draw.rectangle((xmin, ymin, xmax, ymax), outline=color)
        draw.text((xmin, ymin), caption, font=font)

    return np.asarray(viz)
