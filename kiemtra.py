from vnstock import Vnstock
import ta
from datetime import datetime, timedelta

ngay_hom_nay = datetime.now().strftime("%Y-%m-%d")
ngay_bat_dau = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")

ds_ma_can_kiem_tra = ["VNR", "VBB", "BTP", "SCS", "PAN"]

def lay_gia_tri(df_ratio, danh_sach_id_uu_tien, cot):
    for id_can_tim in danh_sach_id_uu_tien:
        hang = df_ratio[df_ratio['item_id'] == id_can_tim]
        if not hang.empty:
            return hang[cot].values[0]
    raise ValueError(f"Không tìm thấy chỉ số trong {danh_sach_id_uu_tien}")

print(f"Ngày kiểm tra: {ngay_hom_nay}\n")

for ma in ds_ma_can_kiem_tra:
    print(f"===== {ma} =====")
    try:
        stock = Vnstock().stock(symbol=ma, source="KBS")

        df = stock.quote.history(start=ngay_bat_dau, end=ngay_hom_nay, interval="1D")
        if df is None or len(df) < 15:
            print("Không đủ dữ liệu giá")
            continue

        df['RSI14'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
        df['RSI7'] = ta.momentum.RSIIndicator(close=df['close'], window=7).rsi()
        df['MFI14'] = ta.volume.MFIIndicator(high=df['high'], low=df['low'], close=df['close'], volume=df['volume'], window=14).money_flow_index()
        df['MFI11'] = ta.volume.MFIIndicator(high=df['high'], low=df['low'], close=df['close'], volume=df['volume'], window=11).money_flow_index()

        vol_tb_10 = df['volume'].tail(10).mean()
        rsi14 = df['RSI14'].iloc[-1]
        rsi7 = df['RSI7'].iloc[-1]
        mfi14 = df['MFI14'].iloc[-1]
        mfi11 = df['MFI11'].iloc[-1]
        gia_dong_cua_moi_nhat = df['close'].iloc[-1]

        chi_so = stock.finance.ratio(period='quarter')
        cot_gan_nhat = [c for c in chi_so.columns if c not in ['item', 'item_id']][0]

        eps_ttm = lay_gia_tri(chi_so, ['trailing_eps'], cot_gan_nhat)
        roa = lay_gia_tri(chi_so, ['roa_trailling', 'roa'], cot_gan_nhat)
        roe = lay_gia_tri(chi_so, ['roe_trailling', 'roe'], cot_gan_nhat)

        pe = (gia_dong_cua_moi_nhat * 1000) / eps_ttm if eps_ttm else None

        print(f"Ngày dữ liệu mới nhất: {df['time'].iloc[-1]}")
        print(f"Giá đóng cửa mới nhất: {gia_dong_cua_moi_nhat}")
        print(f"EPS 4 quý gần nhất: {eps_ttm}")
        print(f"Khối lượng TB 10 phiên: {vol_tb_10:.0f}  ({'ĐẠT' if vol_tb_10 >= 20000 else 'KHÔNG ĐẠT'})")
        print(f"RSI14: {rsi14:.2f}  ({'ĐẠT' if rsi14 < 30 else 'KHÔNG ĐẠT'})")
        print(f"RSI7: {rsi7:.2f}  ({'ĐẠT' if rsi7 < 30 else 'KHÔNG ĐẠT'})")
        print(f"MFI14: {mfi14:.2f}  ({'ĐẠT' if mfi14 < 20 else 'KHÔNG ĐẠT'})")
        print(f"MFI11: {mfi11:.2f}  ({'ĐẠT' if mfi11 < 20 else 'KHÔNG ĐẠT'})")
        print(f"P/E (tự tính): {pe:.2f}  ({'ĐẠT' if pe < 10 else 'KHÔNG ĐẠT'})")
        print(f"ROA bình quân 4 quý: {roa:.2f}%  ({'ĐẠT' if roa > 0 else 'KHÔNG ĐẠT'})")
        print(f"ROE bình quân 4 quý: {roe:.2f}%  ({'ĐẠT' if roe > 5 else 'KHÔNG ĐẠT'})")

    except Exception as e:
        print(f"Lỗi: {e}")

    print()