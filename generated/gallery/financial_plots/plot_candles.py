"""# Candlestick Chart — Daily

OHLC candlestick bars on the busday scale. Wicks use ``vlines``,
bodies use ``bar``. A volume subplot is shown below the price panel.

Core code:

```python
ax_price.set_xscale("busday")
ax_vol.set_xscale("busday")
```

Calendar axes:

- Candlestick price (vlines wicks + bar bodies, green/red)
- Volume bars below with matching colors

Business axes:

- Same artists, weekends compressed
"""

# # %%
# import matplotlib.dates as mdates
# import matplotlib.pyplot as plt
# import numpy as n
# import pandas as pd

# import busdayaxis

# busdayaxis.register_scale()

# rng = np.random.default_rng(42)

# # Daily OHLC data — business days only, centered at noon to avoid weekend edges
# dates = pd.bdate_range("2025-01-01", periods=14)
# draw_times = dates + pd.Timedelta(hours=12)

# returns = rng.normal(0, 0.01, len(dates))
# close = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
# open_ = close.shift(1).fillna(100)
# high = np.maximum(open_.values, close.values) + rng.uniform(0.1, 0.8, len(dates))
# low = np.minimum(open_.values, close.values) - rng.uniform(0.1, 0.8, len(dates))

# colors = ["green" if c >= o else "red" for c, o in zip(close.values, open_.values)]
# body_bottom = np.minimum(open_.values, close.values)
# body_height = np.abs(close.values - open_.values)

# volume = rng.integers(1_000, 10_000, len(dates))

# full_days = pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")
# bar_width = pd.Timedelta(hours=14)

# fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(
#     2, 2, figsize=(10, 6), gridspec_kw={"height_ratios": [3, 1]}
# )
# fig.suptitle("Candlestick Chart — Daily", fontsize=14, fontweight="bold")

# # Set busday scale BEFORE plotting to establish correct axis limits
# ax2.set_xscale("busday")
# ax4.set_xscale("busday")


# def _draw(ax_price, ax_vol):
#     ax_price.vlines(draw_times, low, high, linewidth=1, color="black", zorder=3)
#     ax_price.bar(
#         draw_times,
#         body_height,
#         bottom=body_bottom,
#         width=bar_width,
#         color=colors,
#         zorder=4,
#     )
#     ax_price.set_ylabel("Price")

#     ax_vol.bar(draw_times, volume, color=colors, alpha=0.6, width=bar_width)
#     ax_vol.set_ylabel("Volume", fontsize=8)
#     ax_vol.tick_params(axis="y", labelsize=7)


# # --- Calendar axes ---
# _draw(ax1, ax3)
# ax1.set_title("Calendar Time (scale='linear')")
# ax1.xaxis.set_major_locator(mdates.DayLocator())
# ax1.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
# ax1.tick_params(axis="x", rotation=90, labelbottom=False)
# ax3.xaxis.set_major_locator(mdates.DayLocator())
# ax3.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
# ax3.tick_params(axis="x", rotation=90)

# for d in full_days:
#     if d.weekday() == 5:  # Saturday
#         ax1.axvspan(d, d + pd.Timedelta(days=2), color="grey", alpha=0.15, linewidth=0)
#         ax3.axvspan(d, d + pd.Timedelta(days=2), color="grey", alpha=0.15, linewidth=0)

# # --- Business axes ---
# _draw(ax2, ax4)
# ax2.set_title("Business Time (scale='busday')")
# ax2.xaxis.set_major_locator(busdayaxis.BusdayLocator(mdates.DayLocator()))
# ax2.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
# ax2.tick_params(axis="x", rotation=90, labelbottom=False)
# ax4.xaxis.set_major_locator(busdayaxis.BusdayLocator(mdates.DayLocator()))
# ax4.xaxis.set_major_formatter(mdates.DateFormatter("%a %d %b"))
# ax4.tick_params(axis="x", rotation=90)

# for d in full_days:
#     if d.weekday() == 5:  # Saturday
#         ax2.axvline(d, linestyle="--", linewidth=0.8, alpha=0.6)
#         ax2.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.6)
#         ax4.axvline(d, linestyle="--", linewidth=0.8, alpha=0.6)
#         ax4.axvline(d + pd.Timedelta(days=2), linestyle="--", linewidth=0.8, alpha=0.6)

# plt.tight_layout(rect=[0, 0, 1, 0.96])
# plt.show()

# # %%
# """# Candlestick Chart — Intraday with Business Hours

# The same candlestick construction applied to hourly intraday bars.
# Setting ``bushours=(9, 17)`` compresses pre- and post-market time so
# only the trading session is visible, giving each hour equal visual weight.

# Core code:

# ```python
# ax.set_xscale("busday", bushours=(9, 17))
# ```

# Calendar axis:

# - All hours shown (pre/post market shaded grey)

# Business axis:

# - Only market hours 9:00–17:00 visible, one tick per two hours
# """

# OPEN_H, CLOSE_H = 9, 17

# # Generate hourly bars covering extended hours (7:00–20:00) for 3 business days
# rng2 = np.random.default_rng(99)
# all_hours = [
#     d + pd.Timedelta(hours=h)
#     for d in pd.bdate_range("2025-01-06", periods=3)
#     for h in range(7, 20)
# ]
# bar_times = pd.DatetimeIndex(all_hours)
# draw_times_intra = bar_times + pd.Timedelta(minutes=30)  # center bars within each hour

# ret = rng2.normal(0, 0.003, len(bar_times))
# ret[(bar_times.hour < OPEN_H) | (bar_times.hour >= CLOSE_H)] = 0.0
# close_i = 100 * (1 + pd.Series(ret, index=bar_times)).cumprod()
# open_i = close_i.shift(1).fillna(100)
# high_i = np.maximum(open_i.values, close_i.values) + rng2.uniform(
#     0.01, 0.08, len(bar_times)
# )
# low_i = np.minimum(open_i.values, close_i.values) - rng2.uniform(
#     0.01, 0.08, len(bar_times)
# )

# colors_i = ["green" if c >= o else "red" for c, o in zip(close_i.values, open_i.values)]
# body_bottom_i = np.minimum(open_i.values, close_i.values)
# body_height_i = np.abs(close_i.values - open_i.values)

# bar_width_i = pd.Timedelta(minutes=55)
# full_days_i = pd.date_range(
#     bar_times.min().normalize(), bar_times.max().normalize(), freq="D"
# )

# fig2, (ax5, ax6) = plt.subplots(2, 1, figsize=(10, 6), sharey=True)
# fig2.suptitle(
#     f"Candlestick Chart — Intraday (bushours=({OPEN_H}, {CLOSE_H}))",
#     fontsize=14,
#     fontweight="bold",
# )

# ax6.set_xscale("busday", bushours=(OPEN_H, CLOSE_H))


# def _draw_intra(ax):
#     ax.vlines(draw_times_intra, low_i, high_i, linewidth=0.8, color="black", zorder=3)
#     ax.bar(
#         draw_times_intra,
#         body_height_i,
#         bottom=body_bottom_i,
#         width=bar_width_i,
#         color=colors_i,
#         zorder=4,
#     )
#     ax.set_ylabel("Price")


# # --- Calendar axis ---
# _draw_intra(ax5)
# ax5.set_title("Calendar Time (scale='linear')")
# ax5.xaxis.set_major_locator(mdates.HourLocator(byhour=range(7, 21, 2)))
# ax5.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))
# ax5.tick_params(axis="x", rotation=90)

# for d in full_days_i:
#     ax5.axvspan(
#         d, d + pd.Timedelta(hours=OPEN_H), color="grey", alpha=0.15, linewidth=0
#     )
#     ax5.axvspan(
#         d + pd.Timedelta(hours=CLOSE_H),
#         d + pd.Timedelta(hours=24),
#         color="grey",
#         alpha=0.15,
#         linewidth=0,
#     )

# # --- Business axis ---
# _draw_intra(ax6)
# ax6.set_title(f"Business Time (scale='busday', bushours=({OPEN_H}, {CLOSE_H}))")
# ax6.xaxis.set_major_locator(
#     busdayaxis.BusdayLocator(mdates.HourLocator(byhour=range(OPEN_H, CLOSE_H + 1, 2)))
# )
# ax6.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))
# ax6.tick_params(axis="x", rotation=90)

# for d in full_days_i:
#     ax6.axvline(
#         d + pd.Timedelta(hours=OPEN_H), linestyle="--", linewidth=0.8, alpha=0.6
#     )
#     ax6.axvline(
#         d + pd.Timedelta(hours=CLOSE_H), linestyle="--", linewidth=0.8, alpha=0.6
#     )

# plt.tight_layout(rect=[0, 0, 1, 0.96])
# plt.show()

# # %%
