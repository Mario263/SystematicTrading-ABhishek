//+------------------------------------------------------------------+
//|                                         MACD_Crossover_EA.mq5     |
//|  Hand-rolled MACD crossover EA for the MT5 Strategy Tester.       |
//|  EMA(12)/EMA(26)/MACD/Signal(9) computed by hand, no built-in.    |
//|  Long on MACD crossing above signal; flat on crossing below.      |
//|  Acts once per completed bar.                                     |
//+------------------------------------------------------------------+
#property copyright "Assessment"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input int    FastPeriod   = 12;
input int    SlowPeriod   = 26;
input int    SignalPeriod = 9;
input double LotSize      = 0.10;   // 0.1 lot = 10,000 units (matches vectorbt/Nautilus, D6)
input long   MagicNumber  = 12345;

CTrade trade;

// --- hand-rolled MACD state (persists across ticks/bars) ---
double  emaFast = 0.0, emaSlow = 0.0, signalLine = 0.0;
double  macdLine = 0.0;
double  prevMacd = 0.0, prevSignal = 0.0;
bool    fastInit = false, slowInit = false, signalInit = false;
bool    haveMacd = false, havePrev = false;

int     closeCount = 0;            // closes seen (for SMA seeding)
double  fastSum = 0.0, slowSum = 0.0;
int     macdCount = 0;             // macd values seen (for signal SMA seeding)
double  macdSum = 0.0;

datetime lastBarTime = 0;

//+------------------------------------------------------------------+
double EmaStep(double price, double prevEma, int period)
{
   double k = 2.0 / (period + 1.0);
   return price * k + prevEma * (1.0 - k);
}
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(MagicNumber);
   lastBarTime = 0;
   return(INIT_SUCCEEDED);
}
//+------------------------------------------------------------------+
void OnTick()
{
   // Act only on a newly completed bar
   datetime t = (datetime)SeriesInfoInteger(_Symbol, _Period, SERIES_LASTBAR_DATE);
   if(t == lastBarTime) return;
   lastBarTime = t;

   double close = iClose(_Symbol, _Period, 1);   // index 1 = the just-closed bar
   if(close <= 0.0) return;

   closeCount++;

   // --- fast EMA (seed = SMA of first FastPeriod closes) ---
   if(!fastInit)
   {
      fastSum += close;
      if(closeCount == FastPeriod) { emaFast = fastSum / FastPeriod; fastInit = true; }
   }
   else
      emaFast = EmaStep(close, emaFast, FastPeriod);

   // --- slow EMA (seed = SMA of first SlowPeriod closes) ---
   if(!slowInit)
   {
      slowSum += close;
      if(closeCount == SlowPeriod) { emaSlow = slowSum / SlowPeriod; slowInit = true; }
   }
   else
      emaSlow = EmaStep(close, emaSlow, SlowPeriod);

   if(!fastInit || !slowInit) return;            // MACD not defined yet

   macdLine = emaFast - emaSlow;

   // --- signal = EMA of MACD line (seed = SMA of first SignalPeriod macd values) ---
   if(!signalInit)
   {
      macdCount++;
      macdSum += macdLine;
      if(macdCount == SignalPeriod) { signalLine = macdSum / SignalPeriod; signalInit = true; }
      else { prevMacd = macdLine; return; }      // no signal yet
   }
   else
      signalLine = EmaStep(macdLine, signalLine, SignalPeriod);

   // --- crossover (needs previous bar's macd & signal) ---
   if(havePrev)
   {
      bool crossUp   = (prevMacd <= prevSignal) && (macdLine > signalLine);
      bool crossDown = (prevMacd >= prevSignal) && (macdLine < signalLine);

      bool inPosition = PositionSelect(_Symbol);

      if(crossUp && !inPosition)
         trade.Buy(LotSize, _Symbol);
      else if(crossDown && inPosition)
         trade.PositionClose(_Symbol);
   }

   prevMacd   = macdLine;
   prevSignal = signalLine;
   havePrev   = true;
}
//+------------------------------------------------------------------+
