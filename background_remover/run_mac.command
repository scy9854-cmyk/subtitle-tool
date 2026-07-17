#!/bin/bash
# 맥북에서 더블클릭으로 실행하는 배경 제거 자동화.
# 폴더를 선택하면 그 안의 모든 사진의 배경을 제거하고 흰 배경으로 저장합니다.
cd "$(dirname "$0")" || exit 1

FOLDER=$(osascript -e 'POSIX path of (choose folder with prompt "배경을 제거할 사진들이 있는 폴더를 선택하세요")' 2>/dev/null)

if [ -z "$FOLDER" ]; then
    echo "폴더를 선택하지 않아 종료합니다."
    read -r -p "엔터를 누르면 창이 닫힙니다..."
    exit 1
fi

python3 -m pip install -q -r requirements.txt
python3 remove_background.py "$FOLDER"

echo ""
read -r -p "완료되었습니다. 엔터를 누르면 창이 닫힙니다..."
