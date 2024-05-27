import os
from glob import glob

import matplotlib.pyplot as plt
import numpy as np
import pydicom
from numba import jit
from pydicom.dataset import FileDataset
from pydicom.dicomdir import DicomDir


@jit(nopython=True)
def apply_windowing(
    image: np.ndarray, rows: int, cols: int, minval: float, maxval: float
):
    """
    Apply windowing to the image.

    Parameters
    ----------
    image (np.ndarray)
    * The image to apply windowing.

    rows (int)
    * Number of rows in the image.

    cols (int)
    * Number of columns in the image.

    minval (float)
    * Minimum value for windowing.

    maxval (float)
    * Maximum value for windowing.
    """
    for i in np.arange(rows):
        for j in np.arange(cols):
            result = maxval - minval if maxval - minval != 0 else 1
            image[i, j] = int((image[i, j] - minval) / result * 255)


class Dicom:
    def __init__(self, path: str) -> None:
        """
        Initialize the Dicom object with the given path.

        Parameters
        ----------
        path (str)
        * Path to the DICOM file or directory.
        """
        self.data: list[FileDataset | DicomDir] = self.load(path)
        self.hu_images: np.ndarray

        print(self)

    @staticmethod
    def load(path: str) -> list[FileDataset | DicomDir]:
        """
        Load DICOM files from the given path.

        Parameters
        ----------
        path (str)
        * Path to the DICOM file or directory.

        Returns
        ----------
        list
        * List of DICOM datasets.
        """
        dcm = []

        if os.path.isfile(path):
            try:
                dcm.append(pydicom.dcmread(path))
            except pydicom.errors.InvalidDicomError as e:
                raise RuntimeError(f"Error reading DICOM file: {path}. Error: {e}")

        elif os.path.isdir(path):
            try:
                dcm_files: list[str] = glob(os.path.join(path, "*.dcm"))
                dcm: list[FileDataset | DicomDir] = [
                    pydicom.dcmread(s) for s in dcm_files
                ]
                dcm.sort(key=lambda x: float(x.ImagePositionPatient[2]), reverse=True)
            except (TypeError, pydicom.errors.InvalidDicomError) as e:
                raise RuntimeError(
                    f"Error reading DICOM files in directory: {path}. Error: {e}"
                )

        else:
            raise ValueError(
                f"The provided path '{path}' is neither a file nor a directory."
            )

        return dcm

    def __getitem__(self, index: int):
        """
        Get the pixel array of the DICOM file at the specified index.

        Parameters
        ----------
        index (int)
        * Index of the DICOM file.

        Returns
        ----------
        np.ndarray
        * Pixel array of the DICOM file.
        """
        return self.data[index].pixel_array

    def __str__(self) -> str:
        """
        Get the string representation of the Dicom object.

        Returns
        ----------
        str: String representation of the Dicom object.
        """
        d = self.data[0]
        return (
            f"PatientName:\t{d.PatientName}\n"
            f"PatientID:\t{d.PatientID}\n"
            f"PatientSex:\t{d.PatientSex}\n"
            f"StudyID:\t{d.StudyID}\n"
            f"Rows:\t{d.Rows}\n"
            f"Columns:\t{d.Columns}\n"
            f"SliceThickness:\t{d.SliceThickness}\n"
            f"PixelSpacing:\t{d.PixelSpacing}\n"
            f"WindowCenter:\t{d.WindowCenter}\n"
            f"WindowWidth:\t{d.WindowWidth}\n"
            f"RescaleIntercept:\t{d.RescaleIntercept}\n"
            f"RescaleSlope:\t{d.RescaleSlope}\n"
        )

    def __get_pixel_hu(self) -> np.ndarray:
        """
        Convert the pixel values to Hounsfield Units (HU).

        Returns
        ----------
        np.ndarray
        * 3D array of pixel values in HU.
        """
        images: np.ndarray = np.stack([s.pixel_array for s in self.data])
        images = images.astype(np.int16)
        images[images == -2048] = 0

        for slice_num in range(len(self.data)):
            intercept = self.data[slice_num].RescaleIntercept
            slope = self.data[slice_num].RescaleSlope
            # Some images already have CT values (HU values), in which case the read values are Slope=1 and Intercept=0.
            if slope != 1:
                images[slice_num] = slope * images[slice_num].astype(np.float64).astype(
                    np.int16
                )
            images[slice_num] += np.int16(intercept)

        return images

    def setDicomWinWidthWinCenter(self, winwidth: float = 350, wincenter: float = 60):
        """
        Set the window width and window center for the DICOM images.

        Parameters
        ----------
        winwidth (float)
        * Window width.
        * Lung: 1500; Head: 80; Mediastinum: 400; Bone: 1500

        wincenter (float)
        * Window center.
        * Lung: -400; Head: 40; Mediastinum: 60; Bone: 300
        """

        images: np.ndarray = self.__get_pixel_hu()

        minval: float = (2 * wincenter - winwidth) / 2.0 + 0.5
        maxval: float = (2 * wincenter + winwidth) / 2.0 + 0.5

        for index in range(len(images)):
            img_temp = images[index]
            rows, cols = img_temp.shape
            apply_windowing(img_temp, rows, cols, minval, maxval)
            img_temp[img_temp < 0] = 0
            img_temp[img_temp > 255] = 255
            images[index] = img_temp

        self.hu_images = images

    def show(self, index: int, cmap: str = "o"):
        """
        Show the DICOM image at the specified index.

        Parameters
        ----------
        index (int) :
        * Index of the DICOM image.

        cmap (str) :
        * Color map to be used.
        * "o" for original image, "h" for HU image, "oh" for both original and HU images side by side.
        """

        if cmap == "o":
            fig, ax = plt.subplots()
            image = self[index]
            plt.imshow(image, "gray")

        elif cmap == "h":
            fig, ax = plt.subplots()
            image = self.hu_images[index]
            plt.imshow(image, "gray")

        elif cmap == "oh":
            fig, axes = plt.subplots(1, 2)
            axes[0].imshow(self[index], "gray")
            axes[1].imshow(self.hu_images[index], "gray")

        else:
            raise ValueError(
                "Invalid cmap value. Expected 'o' for original image or 'h' for HU image."
            )

        fig.patch.set_facecolor("black")
        plt.axis("off")
        plt.show()
        plt.close()
