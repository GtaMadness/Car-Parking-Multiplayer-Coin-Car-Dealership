//+------------------------------------------------------------------+
//| ExportATR.mq5                                                     |
//| Exports OHLC + ATR for the chosen symbol/timeframe to a CSV file. |
//| Output: <MT5 data folder>\MQL5\Files\<symbol>_<tf>_ATR<n>.csv     |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input string          InpSymbol    = "XAUUSDm";   // Symbol
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_D1;   // Timeframe (D1 = daily ATR)
input int             InpAtrPeriod = 14;          // ATR period
input int             InpBars      = 200;         // How many bars to export

void OnStart()
{
   int h = iATR(InpSymbol, InpTimeframe, InpAtrPeriod);
   if(h == INVALID_HANDLE) { Print("Could not create ATR: ", GetLastError()); return; }

   double atr[]; MqlRates r[];
   ArraySetAsSeries(atr, true); ArraySetAsSeries(r, true);

   // wait briefly for the indicator to calculate
   for(int i = 0; i < 50 && BarsCalculated(h) <= 0; i++) Sleep(100);

   int n = CopyRates(InpSymbol, InpTimeframe, 0, InpBars, r);
   int m = CopyBuffer(h, 0, 0, InpBars, atr);
   if(n <= 0 || m <= 0) { Print("No data copied. Open the chart once so history loads."); return; }
   n = MathMin(n, m);

   double pip = 0.1;   // gold: 1 pip = $0.10
   string tf  = StringSubstr(EnumToString(InpTimeframe), 7);
   string fn  = StringFormat("%s_%s_ATR%d.csv", InpSymbol, tf, InpAtrPeriod);
   int f = FileOpen(fn, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(f == INVALID_HANDLE) { Print("Could not open file: ", GetLastError()); return; }

   FileWrite(f, "Time", "Open", "High", "Low", "Close", "Range_pips", "ATR", "ATR_pips", "10pct_range_pips");
   for(int i = n - 1; i >= 0; i--)   // oldest first
   {
      double rng = r[i].high - r[i].low;
      FileWrite(f, TimeToString(r[i].time, TIME_DATE | TIME_MINUTES),
                DoubleToString(r[i].open, 3), DoubleToString(r[i].high, 3),
                DoubleToString(r[i].low, 3),  DoubleToString(r[i].close, 3),
                DoubleToString(rng / pip, 1),
                DoubleToString(atr[i], 3), DoubleToString(atr[i] / pip, 1),
                DoubleToString(rng * 0.1 / pip, 1));
   }
   FileClose(f);
   IndicatorRelease(h);
   Print("Saved ", n, " bars to MQL5\\Files\\", fn);
}
