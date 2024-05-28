import os
from glob import glob
from typing import List, Union

from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
import pydicom
from numba import njit
from pydicom.dataset import FileDataset
from pydicom.dicomdir import DicomDir


@njit
def apply_windowing(image: np.ndarray, min_val: float, max_val: float) -> np.ndarray:
    """
    Apply windowing to the image.

    Parameters
    ----------
    image (np.ndarray)
        The image to apply windowing.
    min_val (float)
        Minimum value for windowing.
    max_val (float)
        Maximum value for windowing.

    Returns
    -------
    np.ndarray
        The windowed image.
    """
    windowed_image = np.clip(
        (image - min_val) / (max_val - min_val + 1e-8) * 255, 0, 255
    ).astype(np.uint8)
    return windowed_image


class Dicom:
    def __init__(self, path: str) -> None:
        """
        Initialize the Dicom object with the given path.

        Parameters
        ----------
        path (str)
            Path to the DICOM file or directory.
        """
        self.data: List[Union[FileDataset, DicomDir]] = self._load_data(path)
        self.pixel_data: np.ndarray = self._get_pixel_data()
        self.hu_images: np.ndarray = self._get_hu_images()

        print(self)

    @staticmethod
    def _load_data(path: str) -> List[Union[FileDataset, DicomDir]]:
        """
        Load DICOM files from the given path.

        Parameters
        ----------
        path (str)
            Path to the DICOM file or directory.

        Returns
        ----------
        List[Union[FileDataset, DicomDir]]
            List of DICOM datasets.
        """
        if os.path.isfile(path):
            try:
                return [pydicom.dcmread(path)]
            except pydicom.errors.InvalidDicomError as e:
                raise RuntimeError(f"Error reading DICOM file: {path}. Error: {e}")

        elif os.path.isdir(path):
            try:
                dcm_files: List[str] = glob(os.path.join(path, "*.dcm"))
                dcm_data: List[Union[FileDataset, DicomDir]] = [
                    pydicom.dcmread(s) for s in dcm_files
                ]
                dcm_data.sort(
                    key=lambda x: float(x.ImagePositionPatient[2]), reverse=True
                )
                return dcm_data
            except (TypeError, pydicom.errors.InvalidDicomError) as e:
                raise RuntimeError(
                    f"Error reading DICOM files in directory: {path}. Error: {e}"
                )

        raise ValueError(
            f"The provided path '{path}' is neither a file nor a directory."
        )

    def _get_pixel_data(self) -> np.ndarray:
        """
        Get the pixel data from the DICOM files.

        Returns
        ----------
        np.ndarray
            3D array of pixel data.
        """
        return np.stack([s.pixel_array for s in self.data])

    def _get_hu_images(self) -> np.ndarray:
        """
        Convert the pixel values to Hounsfield Units (HU).

        Returns
        ----------
        np.ndarray
            3D array of pixel values in HU.
        """
        images: np.ndarray = self.pixel_data.astype(np.int16)
        images[images == -2048] = 0

        for index, item in enumerate(self.data):
            intercept = item.RescaleIntercept
            slope = item.RescaleSlope

            if slope != 1:
                images[index] = slope * images[index].astype(np.float64)
            images[index] += np.int16(intercept)

        return images

    def set_window(self, width: float = 350, center: float = 60) -> None:
        """
        Set the window width and window center for the DICOM images.

        Parameters
        ----------
        width (float)
            Window width.
            Lung: 1500; Head: 80; Mediastinum: 400; Bone: 1500
        center (float)
            Window center.
            Lung: -400; Head: 40; Mediastinum: 60; Bone: 300
        """
        min_val = (2 * center - width) / 2.0 + 0.5
        max_val = (2 * center + width) / 2.0 + 0.5
        self.hu_images = apply_windowing(self.hu_images, min_val, max_val)

    def show(self, index: int, mode: str = "original") -> None:
        """
        Show the DICOM image at the specified index.

        Parameters
        ----------
        index (int)
            Index of the DICOM image.
        mode (str)
            Display mode. Can be "original", "hu", or "both".
        """
        if mode == "original" or mode == "o":
            plt.imshow(self.pixel_data[index], cmap="gray")
            plt.title(f"Original-{index}")
            plt.axis("off")
        elif mode == "hu" or mode == "h":
            plt.imshow(self.hu_images[index], cmap="gray")
            plt.title(f"Hounsfield Units-{index}")
            plt.axis("off")
        elif mode == "both" or mode == "oh":
            fig, axes = plt.subplots(1, 2)
            axes[0].imshow(self.pixel_data[index], cmap="gray")
            axes[0].set_title(f"Original-{index}")
            axes[0].axis("off")
            axes[1].imshow(self.hu_images[index], cmap="gray")
            axes[1].set_title(f"Hounsfield Units-{index}")
            axes[1].axis("off")
        else:
            raise ValueError("Invalid mode. Expected 'original', 'hu', or 'both'.")

        # fig.patch.set_facecolor("black")
        plt.tight_layout()
        plt.axis("off")
        plt.show()

    def save_hu_image(self, index: int, save_path: str) -> None:
        """
        Save the HU image at the specified index to the given path.

        Parameters
        ----------
        index (int)
            Index of the DICOM image.
        save_path (str)
            Path to save the HU image.
        """
        os.makedirs(save_path, exist_ok=True)

        image = Image.fromarray(self.hu_images[index])
        filename = os.path.join(save_path, f"{index}_hu.png")
        image.save(filename)

    def save_all_hu_images(self, save_path: str) -> None:
        """
        Save all HU images to the given path.

        Parameters
        ----------
        save_path (str)
            Path to save the HU images.
        """
        os.makedirs(save_path, exist_ok=True)

        for i, image in enumerate(self.hu_images):
            filename = os.path.join(save_path, f"{i}_hu.png")
            img = Image.fromarray(image)
            img.save(filename)

    def __str__(self) -> str:
        """
        Get the string representation of the Dicom object.

        Returns
        ----------
        str: String representation of the Dicom object.
        """
        d = self.data[0]
        return (
            f"PatientName: {d.PatientName}\n"
            f"PatientID: {d.PatientID}\n"
            f"PatientSex: {d.PatientSex}\n"
            f"StudyID: {d.StudyID}\n"
            f"Rows: {d.Rows}\n"
            f"Columns: {d.Columns}\n"
            f"SliceThickness: {d.SliceThickness}\n"
            f"PixelSpacing: {d.PixelSpacing}\n"
            f"WindowCenter: {d.WindowCenter}\n"
            f"WindowWidth: {d.WindowWidth}\n"
            f"RescaleIntercept: {d.RescaleIntercept}\n"
            f"RescaleSlope: {d.RescaleSlope}\n"
        )

    def __getitem__(self, index: int):
        """
        Get the pixel array of the DICOM file at the specified index.

        Parameters
        ----------
        index (int)
            Index of the DICOM file.

        Returns
        ----------
        np.ndarray
            Pixel array of the DICOM file.
        """
        return self.data[index].pixel_array
