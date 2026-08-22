import base64
from io import BytesIO

import qrcode

from src.core.config import settings


class QRCodeGenerator:
    """Service for generating QR codes"""

    def __init__(
            self,
            version: int = 1,
            box_size: int = settings.QR_CODE_BOX_SIZE,
            border: int = settings.QR_CODE_BORDER
    ):
        """
        Initialize QR code generator.

        Args:
            version: QR code version (1-40, controls size)
            box_size: Size of each box in pixels
            border: Border size in boxes
        """
        self.version = version
        self.box_size = box_size
        self.border = border

    def generate_qr_code(
            self,
            data: str,
            fill_color: str = "black",
            back_color: str = "white"
    ) -> bytes:
        """
        Generate QR code image as bytes.

        Args:
            data: Data to encode in QR code
            fill_color: QR code color
            back_color: Background color

        Returns:
            QR code image as bytes
        """
        qr = qrcode.QRCode(
            version=self.version,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=self.box_size,
            border=self.border,
        )

        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color=fill_color, back_color=back_color)

        # Convert to bytes
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        return img_byte_arr.getvalue()

    def generate_qr_code_base64(
            self,
            data: str,
            fill_color: str = "black",
            back_color: str = "white"
    ) -> str:
        """
        Generate QR code as base64 encoded string.

        Args:
            data: Data to encode in QR code
            fill_color: QR code color
            back_color: Background color

        Returns:
            Base64 encoded QR code image string
        """
        qr_bytes = self.generate_qr_code(data, fill_color, back_color)
        base64_encoded = base64.b64encode(qr_bytes).decode('utf-8')
        return f"data:image/png;base64,{base64_encoded}"

    def save_qr_code(
            self,
            data: str,
            filename: str,
            fill_color: str = "black",
            back_color: str = "white"
    ) -> str:
        """
        Generate and save QR code to file.

        Args:
            data: Data to encode in QR code
            filename: Path to save the QR code
            fill_color: QR code color
            back_color: Background color

        Returns:
            Path to saved file
        """
        qr = qrcode.QRCode(
            version=self.version,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=self.box_size,
            border=self.border,
        )

        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color=fill_color, back_color=back_color)
        img.save(filename)

        return filename

    @staticmethod
    def generate_user_qr_data(user_id: int, email: str) -> str:
        """
        Generate standardized QR code data for a user.

        Args:
            user_id: User ID
            email: User email

        Returns:
            Formatted QR code data string
        """
        return f"USER:{user_id}:{email}"

    @staticmethod
    def generate_item_qr_data(item_id: int, item_code: str) -> str:
        """
        Generate standardized QR code data for an inventory item.

        Args:
            item_id: Item ID
            item_code: Item unique code

        Returns:
            Formatted QR code data string
        """
        return f"ITEM:{item_id}:{item_code}"

    @staticmethod
    def parse_qr_data(qr_data: str) -> dict | None:
        """
        Parse QR code data string.

        Args:
            qr_data: QR code data string

        Returns:
            Dictionary with parsed data or None if invalid format
        """
        try:
            parts = qr_data.split(":")
            if len(parts) < 3:
                return None

            qr_type = parts[0]

            if qr_type == "USER":
                return {
                    "type": "user",
                    "id": int(parts[1]),
                    "email": parts[2]
                }
            elif qr_type == "ITEM":
                return {
                    "type": "item",
                    "id": int(parts[1]),
                    "code": parts[2]
                }
            else:
                return None
        except (ValueError, IndexError):
            return None


# Create global instance
qr_generator = QRCodeGenerator()