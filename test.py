import ta
import time
import requests
import csv
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()

import kbs_client

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
FILE_MA_LOI = "ma_loi.csv"

ngay_hom_nay = datetime.now().strftime("%Y-%m-%d")
ngay_bat_dau = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")


def gui_telegram(noi_dung):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": noi_dung}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")


def doc_ma_loi():
    if not os.path.exists(FILE_MA_LOI):
        return set()
    with open(FILE_MA_LOI, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())


def ghi_ma_loi(ma):
    with open(FILE_MA_LOI, 'a', encoding='utf-8') as f:
        f.write(ma + "\n")


def lay_gia_tri(df_ratio, danh_sach_id_uu_tien, cot):
    for id_can_tim in danh_sach_id_uu_tien:
        hang = df_ratio[df_ratio['item_id'] == id_can_tim]
        if not hang.empty:
            return hang[cot].values[0]
    raise ValueError(f"Không tìm thấy chỉ số trong {danh_sach_id_uu_tien}")


ds_ma_goc = kbs_client.danh_sach_co_phieu()

ma_loi_cu = doc_ma_loi()
ds_ma = [m for m in ds_ma_goc if m not in ma_loi_cu]

print(f"Ngày quét: {ngay_hom_nay}")
print(f"Tổng số mã: {len(ds_ma_goc)}, đã loại {len(ma_loi_cu)} mã lỗi cũ, còn quét: {len(ds_ma)}")

ma_vao_vung_mua = []

for i, ma in enumerate(ds_ma):
    print(f"[{i+1}/{len(ds_ma)}] Đang quét: {ma}")
    try:
        df = kbs_client.lich_su_gia(ma, ngay_bat_dau, ngay_hom_nay)
        if df is None or len(df) < 15:
            ghi_ma_loi(ma)
            continue

        df = df[df['volume'] > 0]
        if len(df) < 15:
            ghi_ma_loi(ma)
            continue

        df['RSI14'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
        df['MFI14'] = ta.volume.MFIIndicator(high=df['high'], low=df['low'], close=df['close'], volume=df['volume'], window=14).money_flow_index()

        vol_tb_10 = df['volume'].tail(10).mean()
        rsi_hien_tai = df['RSI14'].iloc[-1]
        mfi_hien_tai = df['MFI14'].iloc[-1]
        gia_dong_cua_moi_nhat = df['close'].iloc[-1]

        chi_so = kbs_client.chi_so_tai_chinh(ma, limit=4)
        if chi_so.empty:
            ghi_ma_loi(ma)
            continue
        cot_gan_nhat = [c for c in chi_so.columns if c not in ['item', 'item_en', 'item_id']][0]

        eps_ttm = lay_gia_tri(chi_so, ['trailing_eps'], cot_gan_nhat)
        roa = lay_gia_tri(chi_so, ['roa_trailling', 'roa'], cot_gan_nhat)
        roe = lay_gia_tri(chi_so, ['roe_trailling', 'roe'], cot_gan_nhat)

        pe = (gia_dong_cua_moi_nhat * 1000) / eps_ttm if eps_ttm else None

        dat_kl = vol_tb_10 >= 20000
        dat_rsi = rsi_hien_tai < 30
        dat_mfi = mfi_hien_tai < 20
        dat_pe = pe is not None and pe < 10
        dat_roa = roa > 0
        dat_roe = roe > 5

        if dat_kl and dat_rsi and dat_mfi and dat_pe and dat_roa and dat_roe:
            ma_vao_vung_mua.append(ma)
            print(f"  -> ✅ {ma} VÀO VÙNG MUA!")

    except Exception as e:
        print(f"  -> Lỗi với {ma}: {e}")
        ghi_ma_loi(ma)

    time.sleep(2.5)

if ma_vao_vung_mua:
    danh_sach_text = ", ".join(ma_vao_vung_mua)
    gui_telegram(f"🔔 CẢNH BÁO VÙNG MUA ({ngay_hom_nay})\nCác mã đạt đủ điều kiện: {danh_sach_text}")
else:
    gui_telegram(f"Quét xong ({ngay_hom_nay}): không có mã nào vào vùng mua lúc này.")

print("\nHoàn tất!")