# Radiverse

This project provides a tool for processing DICOM (Digital Imaging and Communications in Medicine) files, including loading DICOM files, converting pixel values to Hounsfield Units (HU), applying windowing, and displaying DICOM images.

## Usage Example

```python
from radiverse.utils import Dicom
```

### Load DICOM files

```python
# Single image
dcm = Dicom("ct_files/00000001.dcm")

# Folder
dcm = Dicom("ct_files")
```

output:
```
PatientName:	Anonymous
PatientID:	20240527-224912
PatientSex:	M
StudyID:	1706
Rows:	512
Columns:	512
SliceThickness:	1.250000
PixelSpacing:	[0.703125, 0.703125]
WindowCenter:	60
WindowWidth:	350
RescaleIntercept:	-1024
RescaleSlope:	1
```

## Apply windowing

Common (window width, window center) examples:

* Lung: (1500, -400)
* Head: (80, 40)
* Mediastinum: (400, 60)
* Bone: (1500, 300)

```python
dcm.setDicomWinWidthWinCenter(400, 60)
```

## Display

### Original image
```python
dcm.show(0, cmap="o")
```

![](https://p.ipic.vip/npjdkn.png)


### HU image

```python
dcm.show(0, cmap="h")
```

![](https://p.ipic.vip/e2uu4d.png)

### Both original and HU images
```python
dcm.show(0, cmap="oh")
```

![](https://p.ipic.vip/vhsyf1.png)

## Acknowledgments

Special thanks to [3097530495yi](https://aistudio.baidu.com/projectdetail/5351683?channelType=0&channel=0) for providing reference.
