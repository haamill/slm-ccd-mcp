import io
import numpy as np
from PIL import Image
from lab_mcp.imaging.preview import make_preview


def test_preview_keeps_raw_unchanged():
    raw=np.array([[0,2048,4095]],dtype=np.uint16)
    before=raw.copy()
    png,meta=make_preview(raw,12)
    np.testing.assert_array_equal(raw,before)
    np.testing.assert_array_equal(np.asarray(Image.open(io.BytesIO(png))),[[0,128,255]])
    assert meta['white']==4095
