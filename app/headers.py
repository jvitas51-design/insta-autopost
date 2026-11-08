"""Шапка карточки: плашка Metallic и размер со звёздочкой (* = авторская картина @k_hryhorieva).
Шапки берутся из готовых карточек и при необходимости дорабатываются: убрать или добавить звёздочку."""
from PIL import Image
from library import P

H = {'round': 168, 'rect': 140}          # высота шапки над картиной
_cache = {}


def _card(name):
    if name not in _cache:
        _cache[name] = Image.open(P('library', 'templates', 'cards', name + '.png')).convert('RGB')
    return _cache[name]


def _strip(name, half, shape):
    return _card(name).crop((half * 540, 0, half * 540 + 540, H[shape]))


def header(shape, metallic, author):
    """Шапка для левой половины карточки (540 px шириной)."""
    if shape == 'round':
        if metallic and author:
            return _strip('card8', 0, shape)
        if metallic:
            return _strip('card6', 0, shape)
        s = _strip('card9', 0, shape).copy()
        if not author:                                   # убрать звёздочку у «d40*»
            s.paste((255, 255, 255), (494, 60, 530, 120))
        return s
    if metallic:
        s = _strip('card1', 0, shape).copy()
        if not author:                                   # «40x50*» -> «40x50»
            s.paste((255, 255, 255), (499, 45, 522, 95))
        return s
    s = _strip('card7', 0, shape).copy()
    if author:                                           # «40x50» -> «40x50*»
        star = _strip('card1', 0, shape).crop((499, 50, 513, 82))
        s.paste(star, (506, 50))
    return s


def apply(card_img, shape, flags):
    """flags: [(metallic, author), (metallic, author)] для левой и правой картины."""
    for half, (m, a) in enumerate(flags):
        card_img.paste(header(shape, m, a), (half * 540, 0))
    return card_img
