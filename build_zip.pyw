import zipfile
import os

DIST_DIR = "dist"
OUTPUT = "ASoulLittleBun-win-v.zip"


def zip_dist():
    if not os.path.isdir(DIST_DIR):
        print(f"错误: 目录 '{DIST_DIR}' 不存在")
        return

    count = 0
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(DIST_DIR):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, ".")
                zf.write(filepath, arcname)
                count += 1

    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    print(f"打包完成: {OUTPUT}")
    print(f"文件数: {count}")
    print(f"大小: {size_mb:.2f} MB")


if __name__ == "__main__":
    zip_dist()
