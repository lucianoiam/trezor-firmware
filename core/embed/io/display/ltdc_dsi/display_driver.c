/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#pragma GCC optimize("O0")

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/display.h>

#ifdef KERNEL_MODE

#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/systick.h>

#ifdef USE_BACKLIGHT
#include <io/backlight.h>
#endif

#include "display_internal.h"

display_driver_t g_display_driver = {
    .initialized = false,
};

const display_configuration_t g_disp_conf[] = {
  { /* 62MHz, 18.518519MHz, 480px, RGB888 */ 
    .dsi_lane_byte_freq_hz = 62000000ULL,
    .pll_dsi_ndiv = 62,
    .pll_dsi_odf = 2,
    .dsi_dphy_frange = DSI_DPHY_FRANGE_450MHZ_510MHZ,
    .dsi_tx_escape_clk_div = 4, /* 15.5MHz, ~7.75MHz (in LP) */

    .phy_timer_clk_hs2lp = 11,
    .phy_timer_clk_lp2hs = 40,
    .phy_timer_data_hs2lp = 12,
    .phy_timer_data_lp2hs = 23,

    .ltdc_pixel_clock_hz = 18518519ULL,
    .pll3_n = 125,
    .pll3_r = 27,

    .dsi_byte_clk_to_pixel_clk_ratio = 62.0f / 18.518519f,

    .vfp = {2836 /*10Hz*/, 1144 /*20Hz*/, 580 /*30Hz*/, 298 /*40Hz*/, 129 /*50Hz*/, 16 /*60Hz*/},
    .hfp = 56,
    .hact = 480,
    .lcd_width = 480,

    .dsi_pixel_format = DSI_RGB888,
  },
  { /* 62MHz, 18.518519MHz, 430px, RGB888 */ 
    .dsi_lane_byte_freq_hz = 62000000ULL,
    .pll_dsi_ndiv = 62,
    .pll_dsi_odf = 2,
    .dsi_dphy_frange = DSI_DPHY_FRANGE_450MHZ_510MHZ,
    .dsi_tx_escape_clk_div = 4, /* 15.5MHz, ~7.75MHz (in LP) */

    .phy_timer_clk_hs2lp = 11,
    .phy_timer_clk_lp2hs = 40,
    .phy_timer_data_hs2lp = 12,
    .phy_timer_data_lp2hs = 23,

    .ltdc_pixel_clock_hz = 18518519ULL,
    .pll3_n = 125,
    .pll3_r = 27,

    .dsi_byte_clk_to_pixel_clk_ratio = 62.0f / 18.518519f,

    .vfp = {2836 /*10Hz*/, 1144 /*20Hz*/, 580 /*30Hz*/, 298 /*40Hz*/, 129 /*50Hz*/, 16 /*60Hz*/},
    .hfp = 106,
    .hact = 430,
    .lcd_width = 430,

    .dsi_pixel_format = DSI_RGB888,
  },
  { /* 62MHz, 18.518519MHz, 480px, RGB565 */ 
    .dsi_lane_byte_freq_hz = 62000000ULL,
    .pll_dsi_ndiv = 62,
    .pll_dsi_odf = 2,
    .dsi_dphy_frange = DSI_DPHY_FRANGE_450MHZ_510MHZ,
    .dsi_tx_escape_clk_div = 4, /* 15.5MHz, ~7.75MHz (in LP) */

    .phy_timer_clk_hs2lp = 11,
    .phy_timer_clk_lp2hs = 40,
    .phy_timer_data_hs2lp = 12,
    .phy_timer_data_lp2hs = 23,

    .ltdc_pixel_clock_hz = 18518519ULL,
    .pll3_n = 125,
    .pll3_r = 27,

    .dsi_byte_clk_to_pixel_clk_ratio = 62.0f / 18.518519f,

    .vfp = {2836 /*10Hz*/, 1144 /*20Hz*/, 580 /*30Hz*/, 298 /*40Hz*/, 129 /*50Hz*/, 16 /*60Hz*/},
    .hfp = 56,
    .hact = 480,
    .lcd_width = 480,

    .dsi_pixel_format = DSI_RGB565,
  },
  { /* 62MHz, 15.5MHz, 430px, RGB888 */ 
    .dsi_lane_byte_freq_hz = 62000000ULL,
    .pll_dsi_ndiv = 62,
    .pll_dsi_odf = 2,
    .dsi_dphy_frange = DSI_DPHY_FRANGE_450MHZ_510MHZ,
    .dsi_tx_escape_clk_div = 4, /* 15.5MHz, ~7.75MHz (in LP) */

    .phy_timer_clk_hs2lp = 11,
    .phy_timer_clk_lp2hs = 40,
    .phy_timer_data_hs2lp = 12,
    .phy_timer_data_lp2hs = 23,

    .ltdc_pixel_clock_hz = 15500000ULL,
    .pll3_n = 124,
    .pll3_r = 32,

    .dsi_byte_clk_to_pixel_clk_ratio = 62.0f / 15.5f,

    .vfp = {2836 /*10Hz*/, 1144 /*20Hz*/, 580 /*30Hz*/, 298 /*40Hz*/, 129 /*50Hz*/, 16 /*60Hz*/},
    .hfp = 20,
    .hact = 430,
    .lcd_width = 430,

    .dsi_pixel_format = DSI_RGB888,
  },
  { /* 62MHz, 15.5MHz, 430px, RGB565 */ 
    .dsi_lane_byte_freq_hz = 62000000ULL,
    .pll_dsi_ndiv = 62,
    .pll_dsi_odf = 2,
    .dsi_dphy_frange = DSI_DPHY_FRANGE_450MHZ_510MHZ,
    .dsi_tx_escape_clk_div = 4,

    .phy_timer_clk_hs2lp = 11,
    .phy_timer_clk_lp2hs = 40,
    .phy_timer_data_hs2lp = 12,
    .phy_timer_data_lp2hs = 23,

    .ltdc_pixel_clock_hz = 15500000ULL,
    .pll3_n = 124,
    .pll3_r = 32,

    .dsi_byte_clk_to_pixel_clk_ratio = 62.0f / 15.5f,

    .vfp = {2836 /*10Hz*/, 1144 /*20Hz*/, 580 /*30Hz*/, 298 /*40Hz*/, 129 /*50Hz*/, 16 /*60Hz*/},
    .hfp = 20,
    .hact = 430,
    .lcd_width = 430,

    .dsi_pixel_format = DSI_RGB565,
  },
  { /* 16MHz, 15.5MHz, 430px, RGB565 */ 
    .dsi_lane_byte_freq_hz = 16000000ULL,
    .pll_dsi_ndiv = 48,
    .pll_dsi_odf = 6,
    .dsi_dphy_frange = DSI_DPHY_FRANGE_120MHZ_160MHZ,
    .dsi_tx_escape_clk_div = 2, /* 8MHz, 4Mbps */

    .phy_timer_clk_hs2lp = 5,
    .phy_timer_clk_lp2hs = 14,
    .phy_timer_data_hs2lp = 6,
    .phy_timer_data_lp2hs = 11,

    .ltdc_pixel_clock_hz = 15500000ULL,
    .pll3_n = 124,
    .pll3_r = 32,

    .dsi_byte_clk_to_pixel_clk_ratio = 16.0f / 15.5f,

    .vfp = {2836 /*10Hz*/, 1144 /*20Hz*/, 580 /*30Hz*/, 298 /*40Hz*/, 129 /*50Hz*/, 16 /*60Hz*/},
    .hfp = 20,
    .hact = 430,
    .lcd_width = 430,

    .dsi_pixel_format = DSI_RGB565,
  },
  { /* 28.5MHz, 18.518519MHz, 480px, RGB888 */ 
    .dsi_lane_byte_freq_hz = 28500000ULL,
    .pll_dsi_ndiv = 57,
    .pll_dsi_odf = 4,
    .dsi_dphy_frange = DSI_DPHY_FRANGE_200MHZ_240MHZ,
    .dsi_tx_escape_clk_div = 2, /* 14.25MHz, 7.125Mbps */

    .phy_timer_clk_hs2lp = 7,
    .phy_timer_clk_lp2hs = 21,
    .phy_timer_data_hs2lp = 8,
    .phy_timer_data_lp2hs = 15,

    .ltdc_pixel_clock_hz = 18518519ULL,
    .pll3_n = 125,
    .pll3_r = 27,

    .dsi_byte_clk_to_pixel_clk_ratio = 28.5f / 18.518519f,

    .vfp = {2836 /*10Hz*/, 1144 /*20Hz*/, 580 /*30Hz*/, 298 /*40Hz*/, 129 /*50Hz*/, 16 /*60Hz*/},
    .hfp = 56,
    .hact = 480,
    .lcd_width = 480,

    .dsi_pixel_format = DSI_RGB888,
  },
  { /* 56MHz, 18.666667MHz, 480px, RGB888 - DEFAULT/CURRENT config */ 
    .dsi_lane_byte_freq_hz = 56000000ULL,
    .pll_dsi_ndiv = 56,
    .pll_dsi_odf = 2,
    .dsi_dphy_frange = DSI_DPHY_FRANGE_450MHZ_510MHZ,
    .dsi_tx_escape_clk_div = 4,

    .phy_timer_clk_hs2lp = 11,
    .phy_timer_clk_lp2hs = 40,
    .phy_timer_data_hs2lp = 12,
    .phy_timer_data_lp2hs = 23,

    .ltdc_pixel_clock_hz = 18666667ULL,
    .pll3_n = 112,
    .pll3_r = 24,

    .dsi_byte_clk_to_pixel_clk_ratio = 56.0f / 18.666667f,

    .vfp = {16 /*60Hz*/, 16 /*60Hz*/, 16 /*60Hz*/, 16 /*60Hz*/, 16 /*60Hz*/, 16 /*60Hz*/},
    .hfp = 56,
    .hact = 480,
    .lcd_width = 480,

    .dsi_pixel_format = DSI_RGB888,
  },
  { /* 62MHz, 18.518519MHz, 430px, RGB565 */ 
    .dsi_lane_byte_freq_hz = 62000000ULL,
    .pll_dsi_ndiv = 62,
    .pll_dsi_odf = 2,
    .dsi_dphy_frange = DSI_DPHY_FRANGE_450MHZ_510MHZ,
    .dsi_tx_escape_clk_div = 4, /* 15.5MHz, ~7.75MHz (in LP) */

    .phy_timer_clk_hs2lp = 11,
    .phy_timer_clk_lp2hs = 40,
    .phy_timer_data_hs2lp = 12,
    .phy_timer_data_lp2hs = 23,

    .ltdc_pixel_clock_hz = 18518519ULL,
    .pll3_n = 125,
    .pll3_r = 27,

    .dsi_byte_clk_to_pixel_clk_ratio = 62.0f / 18.518519f,

    .vfp = {2836 /*10Hz*/, 1144 /*20Hz*/, 580 /*30Hz*/, 298 /*40Hz*/, 129 /*50Hz*/, 16 /*60Hz*/},
    .hfp = 106,
    .hact = 430,
    .lcd_width = 430,

    .dsi_pixel_format = DSI_RGB565,
  },
};

const uint8_t conf_idx = 1;

static void display_pll_deinit(void) { __HAL_RCC_PLL3_DISABLE(); }

static bool display_pll_init(void) {
  /* Start and configure PLL3 */
  /* HSE = 16/32MHZ */
  /* 16/32/(M=8) = 4MHz input (min) */
  /* 4*(N=125) = 500MHz VCO (almost max) */
  /* 500/(P=8) = 62.5 for DSI is exactly the lane byte clock*/

  __HAL_RCC_PLL3_DISABLE();

  while (__HAL_RCC_GET_FLAG(RCC_FLAG_PLL3RDY) != 0U)
    ;

#if HSE_VALUE == 32000000
  // (((32 MHz / 8) * 125) / 27) = ~60 Hz
  __HAL_RCC_PLL3_CONFIG(RCC_PLLSOURCE_HSE, 8, g_disp_conf[conf_idx].pll3_n, 8, 8, g_disp_conf[conf_idx].pll3_r); 
#elif HSE_VALUE == 16000000
  // (((16 MHz / 4) * 125) / 27) = ~60 Hz
  __HAL_RCC_PLL3_CONFIG(RCC_PLLSOURCE_HSE, 4, g_disp_conf[conf_idx].pll3_n, 8, 8, g_disp_conf[conf_idx].pll3_r);
#endif

  __HAL_RCC_PLL3_VCIRANGE(RCC_PLLVCIRANGE_0);

  __HAL_RCC_PLL3CLKOUT_ENABLE(RCC_PLL3_DIVR | RCC_PLL3_DIVP);

  __HAL_RCC_PLL3FRACN_DISABLE();

  __HAL_RCC_PLL3_ENABLE();

  /* Wait till PLL3 is ready */
  while (__HAL_RCC_GET_FLAG(RCC_FLAG_PLL3RDY) == 0U)
    ;

  __HAL_RCC_DSI_CONFIG(RCC_DSICLKSOURCE_PLL3);
  __HAL_RCC_LTDC_CONFIG(RCC_LTDCCLKSOURCE_PLL3);

  return true;
}

static void display_dsi_deinit(display_driver_t *drv) {
  __HAL_RCC_DSI_CLK_DISABLE();
  __HAL_RCC_DSI_FORCE_RESET();
  __HAL_RCC_DSI_RELEASE_RESET();
  memset(&drv->hlcd_dsi, 0, sizeof(drv->hlcd_dsi));
}

static bool display_dsi_init(display_driver_t *drv) {
  DSI_PLLInitTypeDef PLLInit = {0};
  DSI_PHY_TimerTypeDef PhyTimers = {0};
  DSI_HOST_TimeoutTypeDef HostTimeouts = {0};

  __HAL_RCC_DSI_FORCE_RESET();
  __HAL_RCC_DSI_RELEASE_RESET();

  /* Enable DSI clock */
  __HAL_RCC_DSI_CLK_ENABLE();

  /* Switch to D-PHY source clock */
  /* Enable the DSI host */
  drv->hlcd_dsi.Instance = DSI;

  __HAL_DSI_ENABLE(&drv->hlcd_dsi);

  // /* Enable the DSI PLL */
  __HAL_DSI_PLL_ENABLE(&drv->hlcd_dsi);

  HAL_Delay(1);

  /* Enable the clock lane and the digital section of the D-PHY   */
  drv->hlcd_dsi.Instance->PCTLR |= (DSI_PCTLR_CKE | DSI_PCTLR_DEN);

  /* Set the TX escape clock division factor */
  drv->hlcd_dsi.Instance->CCR = 4;

  HAL_Delay(1);

  /* Config DSI Clock to DSI PHY */
  __HAL_RCC_DSI_CONFIG(RCC_DSICLKSOURCE_DSIPHY);

  /* Reset the TX escape clock division factor */
  drv->hlcd_dsi.Instance->CCR &= ~DSI_CCR_TXECKDIV;

  /* Disable the DSI PLL */
  __HAL_DSI_PLL_DISABLE(&drv->hlcd_dsi);

  /* Disable the DSI host */
  __HAL_DSI_DISABLE(&drv->hlcd_dsi);

  /* DSI initialization */
  drv->hlcd_dsi.Instance = DSI;
  drv->hlcd_dsi.Init.AutomaticClockLaneControl = DSI_AUTO_CLK_LANE_CTRL_DISABLE; // Erratum "DSI automatic clock lane control not functional"
  /* We have 2 data lanes at 496Mbps => lane byte clock at 496/8 = 62 MHZ */
  /* We want TX escape clock at around 20MHz and under 20MHz so clock division
   * is set to 4 */
  drv->hlcd_dsi.Init.TXEscapeCkdiv = g_disp_conf[conf_idx].dsi_tx_escape_clk_div; // ~15.5 MHz => ~7.75 Mbps (in LP)
  drv->hlcd_dsi.Init.NumberOfLanes = PANEL_DSI_LANES;
  drv->hlcd_dsi.Init.PHYFrequencyRange = g_disp_conf[conf_idx].dsi_dphy_frange;
  drv->hlcd_dsi.Init.PHYLowPowerOffset = PHY_LP_OFFSSET_0_CLKP; // LPXO - no offset

#if HSE_VALUE == 32000000
  // Output lane byte clock = 62 MHz, PHY clock = 496 MHz
  // (((32 MHz / 4) * 62) / 8) = 62 MHz
  PLLInit.PLLNDIV = g_disp_conf[conf_idx].pll_dsi_ndiv;
#elif HSE_VALUE == 16000000
  // Output lane byte clock = 62 MHz, PHY clock = 496 MHz
  // (((16 MHz / 4) * 124) / 8) = 62 MHz
  PLLInit.PLLNDIV = g_disp_conf[conf_idx].pll_dsi_ndiv * 2;
#endif
  PLLInit.PLLIDF = 4;
  PLLInit.PLLODF = g_disp_conf[conf_idx].pll_dsi_odf;
  PLLInit.PLLVCORange = DSI_DPHY_VCO_FRANGE_800MHZ_1GHZ;
  PLLInit.PLLChargePump = DSI_PLL_CHARGE_PUMP_2000HZ_4400HZ;
  PLLInit.PLLTuning = DSI_PLL_LOOP_FILTER_2000HZ_4400HZ;

  if (HAL_DSI_Init(&drv->hlcd_dsi, &PLLInit) != HAL_OK) {
    goto cleanup;
  }
  if (HAL_DSI_SetGenericVCID(&drv->hlcd_dsi, 0) != HAL_OK) {
    goto cleanup;
  }

  /* Configure the DSI for Video mode */
  drv->DSIVidCfg.VirtualChannelID = 0;
  drv->DSIVidCfg.HSPolarity = DSI_HSYNC_ACTIVE_HIGH;
  drv->DSIVidCfg.VSPolarity = DSI_VSYNC_ACTIVE_HIGH;
  drv->DSIVidCfg.DEPolarity = DSI_DATA_ENABLE_ACTIVE_HIGH;
  drv->DSIVidCfg.ColorCoding = g_disp_conf[conf_idx].dsi_pixel_format;
  drv->DSIVidCfg.Mode = PANEL_DSI_MODE;
  drv->DSIVidCfg.PacketSize = g_disp_conf[conf_idx].lcd_width; // In burst mode, the packet size must
                                         // be great or equal to the visible
                                         // width
  drv->DSIVidCfg.NumberOfChunks = 0; // No chunks in burst mode
  drv->DSIVidCfg.NullPacketSize = 0; // No null packet in burst mode
  drv->DSIVidCfg.HorizontalSyncActive = HSYNC * g_disp_conf[conf_idx].dsi_byte_clk_to_pixel_clk_ratio;
  drv->DSIVidCfg.HorizontalBackPorch = HBP * g_disp_conf[conf_idx].dsi_byte_clk_to_pixel_clk_ratio;
  drv->DSIVidCfg.HorizontalLine = (g_disp_conf[conf_idx].hact + HSYNC + HBP + g_disp_conf[conf_idx].hfp) * g_disp_conf[conf_idx].dsi_byte_clk_to_pixel_clk_ratio;
  drv->DSIVidCfg.VerticalSyncActive = VSYNC;
  drv->DSIVidCfg.VerticalBackPorch = VBP;
  drv->DSIVidCfg.VerticalFrontPorch = g_disp_conf[conf_idx].vfp[5]; // Default to 60Hz
  drv->DSIVidCfg.VerticalActive = VACT;
  drv->DSIVidCfg.LPCommandEnable = DSI_LP_COMMAND_ENABLE;
  drv->DSIVidCfg.LPLargestPacketSize = 64;
  /* Specify for each region of the video frame, if the transmission of command
   * in LP mode is allowed in this region */
  /* while streaming is active in video mode */
  drv->DSIVidCfg.LPHorizontalFrontPorchEnable = DSI_LP_HFP_ENABLE;
  drv->DSIVidCfg.LPHorizontalBackPorchEnable = DSI_LP_HBP_ENABLE;
  drv->DSIVidCfg.LPVerticalActiveEnable = DSI_LP_VACT_ENABLE;
  drv->DSIVidCfg.LPVerticalFrontPorchEnable = DSI_LP_VFP_ENABLE;
  drv->DSIVidCfg.LPVerticalBackPorchEnable = DSI_LP_VBP_ENABLE;
  drv->DSIVidCfg.LPVerticalSyncActiveEnable = DSI_LP_VSYNC_ENABLE;
  drv->DSIVidCfg.FrameBTAAcknowledgeEnable = DSI_FBTAA_ENABLE;
  drv->DSIVidCfg.LooselyPacked = DSI_LOOSELY_PACKED_DISABLE;

  /* Drive the display */
  if (HAL_DSI_ConfigVideoMode(&drv->hlcd_dsi, &drv->DSIVidCfg) != HAL_OK) {
    goto cleanup;
  }

  /*********************/
  /* LCD configuration */
  /*********************/
  // RM0456 Table 445. HS2LP and LP2HS values vs. band frequency (MHz)
  PhyTimers.ClockLaneHS2LPTime = g_disp_conf[conf_idx].phy_timer_clk_hs2lp;
  PhyTimers.ClockLaneLP2HSTime = g_disp_conf[conf_idx].phy_timer_clk_lp2hs;
  PhyTimers.DataLaneHS2LPTime = g_disp_conf[conf_idx].phy_timer_data_hs2lp;
  PhyTimers.DataLaneLP2HSTime = g_disp_conf[conf_idx].phy_timer_data_lp2hs;
  PhyTimers.DataLaneMaxReadTime = 0;
  PhyTimers.StopWaitTime = 7;

  if (HAL_DSI_ConfigPhyTimer(&drv->hlcd_dsi, &PhyTimers)) {
    goto cleanup;
  }

  HostTimeouts.TimeoutCkdiv = 1;
  HostTimeouts.HighSpeedTransmissionTimeout = 0;
  HostTimeouts.LowPowerReceptionTimeout = 0;
  HostTimeouts.HighSpeedReadTimeout = 0;
  HostTimeouts.LowPowerReadTimeout = 0;
  HostTimeouts.HighSpeedWriteTimeout = 0;
  HostTimeouts.HighSpeedWritePrespMode = 0;
  HostTimeouts.LowPowerWriteTimeout = 0;
  HostTimeouts.BTATimeout = 0;

  if (HAL_DSI_ConfigHostTimeouts(&drv->hlcd_dsi, &HostTimeouts) != HAL_OK) {
    goto cleanup;
  }

  if (HAL_DSI_ConfigFlowControl(&drv->hlcd_dsi, DSI_FLOW_CONTROL_BTA) !=
      HAL_OK) {
    goto cleanup;
  }

  // The LTDC clock must be disabled before enabling the DSI host.
  // If the LTDC clock remains enabled, the display colors may appear
  // incorrectly or randomly swapped.
  __HAL_RCC_LTDC_CLK_DISABLE();

  /* Enable the DSI host */
  __HAL_DSI_ENABLE(&drv->hlcd_dsi);

  return true;

cleanup:
  display_dsi_deinit(drv);
  return false;
}

static bool display_ltdc_config_layer(LTDC_HandleTypeDef *hltdc,
                                      uint32_t fb_addr) {
  LTDC_LayerCfgTypeDef LayerCfg = {0};

  /* LTDC layer configuration */
  LayerCfg.WindowX0 = LCD_X_OFFSET;
  LayerCfg.WindowX1 = DISPLAY_RESX + LCD_X_OFFSET;
  LayerCfg.WindowY0 = LCD_Y_OFFSET;
  LayerCfg.WindowY1 = DISPLAY_RESY + LCD_Y_OFFSET;
  LayerCfg.PixelFormat = PANEL_LTDC_PIXEL_FORMAT;
  LayerCfg.Alpha = 0xFF; /* NU default value */
  LayerCfg.Alpha0 = 0;   /* NU default value */
  LayerCfg.BlendingFactor1 =
      LTDC_BLENDING_FACTOR1_PAxCA; /* Not Used: default value */
  LayerCfg.BlendingFactor2 =
      LTDC_BLENDING_FACTOR2_PAxCA; /* Not Used: default value */
  LayerCfg.FBStartAdress = fb_addr;
  LayerCfg.ImageWidth =
      FRAME_BUFFER_PIXELS_PER_LINE; /* Number of pixels per line in virtual
                                       frame buffer */
  LayerCfg.ImageHeight = LCD_HEIGHT;
  LayerCfg.Backcolor.Red = 0;   /* Not Used: default value */
  LayerCfg.Backcolor.Green = 0; /* Not Used: default value */
  LayerCfg.Backcolor.Blue = 0xFF; // TEST /* Not Used: default value */
  LayerCfg.Backcolor.Reserved = 0xFF;
  return HAL_LTDC_ConfigLayer(hltdc, &LayerCfg, LTDC_LAYER_1) == HAL_OK;
}

void display_ltdc_deinit(display_driver_t *drv) {
  __HAL_RCC_LTDC_CLK_DISABLE();
  __HAL_RCC_LTDC_FORCE_RESET();
  __HAL_RCC_LTDC_RELEASE_RESET();
}

static bool display_ltdc_init(display_driver_t *drv, uint32_t fb_addr) {
  __HAL_RCC_LTDC_FORCE_RESET();
  __HAL_RCC_LTDC_RELEASE_RESET();

  __HAL_RCC_LTDC_CLK_ENABLE();

  /* LTDC initialization */
  drv->hlcd_ltdc.Instance = LTDC;
  drv->hlcd_ltdc.Init.HSPolarity = LTDC_HSPOLARITY_AL;
  drv->hlcd_ltdc.Init.VSPolarity = LTDC_VSPOLARITY_AL;
  drv->hlcd_ltdc.Init.DEPolarity = LTDC_DEPOLARITY_AL;
  drv->hlcd_ltdc.Init.PCPolarity = LTDC_PCPOLARITY_IPC;
  drv->hlcd_ltdc.Init.HorizontalSync = HSYNC - 1;
  drv->hlcd_ltdc.Init.AccumulatedHBP = HSYNC + HBP - 1;
  drv->hlcd_ltdc.Init.AccumulatedActiveW = g_disp_conf[conf_idx].hact + HBP + HSYNC - 1;
  drv->hlcd_ltdc.Init.TotalWidth = g_disp_conf[conf_idx].hact + HBP + g_disp_conf[conf_idx].hfp + HSYNC - 1;
  drv->hlcd_ltdc.Init.Backcolor.Red = 0xFF; // TEST  /* Not used default value */
  drv->hlcd_ltdc.Init.Backcolor.Green = 0; /* Not used default value */
  drv->hlcd_ltdc.Init.Backcolor.Blue = 0;  /* Not used default value */
  drv->hlcd_ltdc.Init.Backcolor.Reserved = 0xFF;

  if (HAL_LTDCEx_StructInitFromVideoConfig(&drv->hlcd_ltdc, &drv->DSIVidCfg) !=
      HAL_OK) {
    goto cleanup;
  }

  if (HAL_LTDC_Init(&drv->hlcd_ltdc) != HAL_OK) {
    goto cleanup;
  }

  if (!display_ltdc_config_layer(&drv->hlcd_ltdc, fb_addr)) {
    goto cleanup;
  }

  return true;

cleanup:
  display_ltdc_deinit(drv);
  return false;
}

bool display_set_fb(uint32_t fb_addr) {
  display_driver_t *drv = &g_display_driver;
  return display_ltdc_config_layer(&drv->hlcd_ltdc, fb_addr);
}

// This implementation does not support `mode` parameter, it
// behaves as if `mode` is always `DISPLAY_RESET_CONTENT`.
bool display_init(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (drv->initialized) {
    return true;
  }

  GPIO_InitTypeDef GPIO_InitStructure = {0};

#ifdef DISPLAY_PWREN_PIN
  DISPLAY_PWREN_CLK_ENA();
  HAL_GPIO_WritePin(DISPLAY_PWREN_PORT, DISPLAY_PWREN_PIN, GPIO_PIN_RESET);
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
  GPIO_InitStructure.Pin = DISPLAY_PWREN_PIN;
  HAL_GPIO_Init(DISPLAY_PWREN_PORT, &GPIO_InitStructure);
#endif

#ifdef DISPLAY_RESET_PIN
  DISPLAY_RESET_CLK_ENA();
  HAL_GPIO_WritePin(GPIOE, DISPLAY_RESET_PIN, GPIO_PIN_RESET);
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
  GPIO_InitStructure.Pin = DISPLAY_RESET_PIN;
  HAL_GPIO_Init(DISPLAY_RESET_PORT, &GPIO_InitStructure);

  systick_delay_ms(10);
  HAL_GPIO_WritePin(DISPLAY_RESET_PORT, DISPLAY_RESET_PIN, GPIO_PIN_SET);
  systick_delay_ms(120);
#endif

#ifdef USE_BACKLIGHT
  backlight_init(BACKLIGHT_RESET, GAMMA_EXP);
#endif

  uint32_t fb_addr = display_fb_init();

#ifdef DISPLAY_GFXMMU
  display_gfxmmu_init(drv);
#endif

  if (!display_pll_init()) {
    goto cleanup;
  }
  if (!display_dsi_init(drv)) {
    goto cleanup;
  }
  if (!display_ltdc_init(drv, fb_addr)) {
    goto cleanup;
  }

  /* Start DSI */
  if (HAL_DSI_Start(&drv->hlcd_dsi) != HAL_OK) {
    goto cleanup;
  }

  if (!panel_init(drv)) {
    goto cleanup;
  }

  if (HAL_LTDC_ProgramLineEvent(&drv->hlcd_ltdc, LCD_HEIGHT) != HAL_OK) {
    goto cleanup;
  }

  /* Enable LTDC interrupt */
  NVIC_SetPriority(LTDC_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(LTDC_IRQn);

  NVIC_SetPriority(LTDC_ER_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(LTDC_ER_IRQn);

  __HAL_LTDC_ENABLE_IT(&drv->hlcd_ltdc, LTDC_IT_LI | LTDC_IT_FU | LTDC_IT_TE);

  gfx_bitblt_init();

  drv->initialized = true;
  return true;

cleanup:
  display_deinit(DISPLAY_RESET_CONTENT);
  return false;
}

// This implementation does not support `mode` parameter, it
// behaves as if `mode` is always `DISPLAY_RESET_CONTENT`.
void display_deinit(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  gfx_bitblt_deinit();

  NVIC_DisableIRQ(LTDC_IRQn);
  NVIC_DisableIRQ(LTDC_ER_IRQn);

#ifdef BACKLIGHT_PIN_PIN
  HAL_GPIO_DeInit(BACKLIGHT_PIN_PORT, BACKLIGHT_PIN_PIN);
#endif

#ifdef USE_BACKLIGHT
  backlight_deinit(BACKLIGHT_RESET);
#endif

  display_dsi_deinit(drv);
  display_ltdc_deinit(drv);
#ifdef DISPLAY_GFXMMU
  display_gfxmmu_deinit(drv);
#endif
  display_pll_deinit();

#ifdef DISPLAY_RESET_PIN
  // Release the RESET pin
  HAL_GPIO_DeInit(DISPLAY_RESET_PORT, DISPLAY_RESET_PIN);
#endif

#ifdef DISPLAY_PWREN_PIN
  // Release PWREN pin and switch display power off
  HAL_GPIO_DeInit(DISPLAY_PWREN_PORT, DISPLAY_PWREN_PIN);
#endif

  memset(drv, 0, sizeof(display_driver_t));
}

void display_refresh_rate_set(uint32_t new_vfp) {
  display_driver_t *drv = &g_display_driver;
  irq_key_t key;

  if (!drv->initialized) {
    return;
  }

  key = irq_lock();

  while ((drv->hlcd_ltdc.Instance->CDSR & LTDC_CDSR_VSYNCS_Msk) != 0)
    continue;

  while ((drv->hlcd_ltdc.Instance->CDSR & LTDC_CDSR_VSYNCS_Msk) == 0)
    continue;

  drv->hlcd_ltdc.Instance->GCR &= ~LTDC_GCR_LTDCEN;
  drv->hlcd_dsi.Instance->CR &= ~DSI_CR_EN;

  drv->DSIVidCfg.VerticalFrontPorch = new_vfp;
  drv->hlcd_ltdc.Init.TotalHeigh = drv->hlcd_ltdc.Init.AccumulatedActiveH +
                                   drv->DSIVidCfg.VerticalFrontPorch;

  /* Set the Vertical Front Porch (VFP)*/
  drv->hlcd_dsi.Instance->VVFPCR &= ~(DSI_VVFPCR_VFP);
  drv->hlcd_dsi.Instance->VVFPCR |= drv->DSIVidCfg.VerticalFrontPorch;  

  /* Set Total Height */
  drv->hlcd_ltdc.Instance->TWCR &= ~0xFFFF/*~(LTDC_TWCR_TOTALH)*/;
  drv->hlcd_ltdc.Instance->TWCR |= drv->hlcd_ltdc.Init.TotalHeigh;

  drv->hlcd_dsi.Instance->CR |= DSI_CR_EN;
  drv->hlcd_ltdc.Instance->GCR |= LTDC_GCR_LTDCEN;

  irq_unlock(key);
}

bool display_set_backlight(uint8_t level) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return false;
  }

#ifdef USE_BACKLIGHT
  if (level > 0 && backlight_get() == 0) {
    display_ensure_refreshed();
  }

  return backlight_set(level);
#else
  // Just emulation, not doing anything
  drv->backlight_level = level;
  return true;
#endif
}

uint8_t display_get_backlight(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }
#ifdef USE_BACKLIGHT
  return backlight_get();
#else
  return drv->backlight_level;
#endif
}

int display_set_orientation(int angle) { return angle; }

int display_get_orientation(void) { return 0; }

void LTDC_IRQHandler(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mode = mpu_reconfig(MPU_MODE_DEFAULT);

  display_driver_t *drv = &g_display_driver;

  if (drv->hlcd_ltdc.State != HAL_LTDC_STATE_RESET) {
    HAL_LTDC_IRQHandler(&drv->hlcd_ltdc);
  } else {
    LTDC->ICR = 0x3F;
  }

  mpu_restore(mode);
  IRQ_LOG_EXIT();
}

void LTDC_ER_IRQHandler(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mode = mpu_reconfig(MPU_MODE_DEFAULT);

  display_driver_t *drv = &g_display_driver;

  if (drv->hlcd_ltdc.State != HAL_LTDC_STATE_RESET) {
    HAL_LTDC_IRQHandler(&drv->hlcd_ltdc);
  } else {
    LTDC->ICR = 0x3F;
  }

  mpu_restore(mode);
  IRQ_LOG_EXIT();
}

#endif
