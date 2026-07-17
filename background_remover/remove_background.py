#!/usr/bin/env python3
"""여러 장의 사진에서 배경(누끼)을 따고 흰 배경으로 합성해 저장하는 배치 자동화 스크립트.

사용법:
    python3 remove_background.py <입력_폴더> [출력_폴더]

- 입력 폴더 안의 이미지(jpg, jpeg, png, heic, heif, webp, bmp, tiff)를 모두 처리합니다.
- 출력 폴더를 생략하면 입력 폴더 옆에 "<입력_폴더명>_white_bg" 폴더를 만듭니다.
- 결과물은 항상 JPG로 저장됩니다.

최초 실행 시 배경 제거 AI 모델(u2net, 약 170MB)을 인터넷에서 한 번 내려받습니다.
이후에는 인터넷 연결 없이 동작합니다.
"""
import sys
from pathlib import Path

from PIL import Image
from rembg import remove

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".bmp", ".tiff"}


def remove_background_to_white(image_path: Path, output_path: Path) -> None:
    with Image.open(image_path) as img:
        cutout = remove(img.convert("RGBA"))

    white_bg = Image.new("RGBA", cutout.size, (255, 255, 255, 255))
    white_bg.alpha_composite(cutout)
    white_bg.convert("RGB").save(output_path, "JPEG", quality=95)


def main() -> None:
    if len(sys.argv) < 2:
        print("사용법: python3 remove_background.py <입력_폴더> [출력_폴더]")
        sys.exit(1)

    input_dir = Path(sys.argv[1]).expanduser().resolve()
    if not input_dir.is_dir():
        print(f"입력 폴더를 찾을 수 없습니다: {input_dir}")
        sys.exit(1)

    output_dir = (
        Path(sys.argv[2]).expanduser().resolve()
        if len(sys.argv) > 2
        else input_dir.parent / f"{input_dir.name}_white_bg"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    images = sorted(
        p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not images:
        print(f"{input_dir}에서 처리할 이미지를 찾지 못했습니다.")
        sys.exit(1)

    print(f"{len(images)}개 이미지를 처리합니다 -> {output_dir}")
    failures = []
    for i, image_path in enumerate(images, 1):
        output_path = output_dir / f"{image_path.stem}.jpg"
        try:
            remove_background_to_white(image_path, output_path)
            print(f"[{i}/{len(images)}] 완료: {image_path.name} -> {output_path.name}")
        except Exception as e:
            failures.append(image_path.name)
            print(f"[{i}/{len(images)}] 실패: {image_path.name} ({e})")

    print(f"\n전체 작업 완료: 성공 {len(images) - len(failures)}개, 실패 {len(failures)}개")
    if failures:
        print("실패한 파일: " + ", ".join(failures))


if __name__ == "__main__":
    main()
