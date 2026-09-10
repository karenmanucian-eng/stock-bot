from vnstock import Vnstock
import ta
import time
import requests
import csv
import os

from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
FILE_MA_LOI = "ma_loi.csv"

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

vnstock = Vnstock()
listing = vnstock.stock(symbol="ACB", source="KBS").listing
danh_sach = listing.symbols_by_exchange()
chi_co_phieu = danh_sach[danh_sach['type'] == 'stock']
ds_ma_goc = chi_co_phieu['symbol'].tolist()

ma_loi_cu = doc_ma_loi()
ds_ma = [m for m in ds_ma_goc if m not in ma_loi_cu]

print(f"Tổng số mã: {len(ds_ma_goc)}, đã loại {len(ma_loi_cu)} mã lỗi cũ, còn quét: {len(ds_ma)}")

ma_vao_vung_mua = []

for i, ma in enumerate(ds_ma):
    print(f"[{i+1}/{len(ds_ma)}] Đang quét: {ma}")
    try:
        stock = vnstock.stock(symbol=ma, source="KBS")

        df = stock.quote.history(start="2026-06-01", end="2026-09-07", interval="1D")
        if df is None or len(df) < 15:
            ghi_ma_loi(ma)
            continue

        df['RSI14'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
        df['MFI14'] = ta.volume.MFIIndicator(high=df['high'], low=df['low'], close=df['close'], volume=df['volume'], window=14).money_flow_index()

        vol_tb_10 = df['volume'].tail(10).mean()
        rsi_hien_tai = df['RSI14'].iloc[-1]
        mfi_hien_tai = df['MFI14'].iloc[-1]

        chi_so = stock.finance.ratio(period='quarter')
        quy_gan_nhat = [c for c in chi_so.columns if c not in ['item', 'item_id']][0]

        hang_pe = chi_so[chi_so['item'].str.contains('P/E', na=False)]
        pe = hang_pe[quy_gan_nhat].values[0]

        hang_roa = chi_so[chi_so['item'].str.contains('ROA', na=False)]
        roa = hang_roa[quy_gan_nhat].values[0]

        hang_roe = chi_so[chi_so['item'].str.contains('ROE', na=False)]
        roe = hang_roe[quy_gan_nhat].values[0]

        dat_kl = vol_tb_10 >= 20000
        dat_rsi = rsi_hien_tai < 30
        dat_mfi = mfi_hien_tai < 20
        dat_pe = pe < 10
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
    gui_telegram(f"🔔 CẢNH BÁO VÙNG MUA\nCác mã đạt đủ điều kiện: {danh_sach_text}")
else:
    gui_telegram("Quét xong: không có mã nào vào vùng mua lúc này.")

print("\nHoàn tất!")