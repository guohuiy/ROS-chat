import React, { useMemo } from 'react';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { PieChart, BarChart } from 'echarts/charts';
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { useAppStore } from '../store';

// 注册 ECharts 组件
echarts.use([
  PieChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  CanvasRenderer,
]);


/** 对象实时统计面板 - 显示检测对象的数量和分布 */
const StatsPanel: React.FC = () => {
  const { objectStats, isCameraOn, detections } = useAppStore();

  // 饼图配置
  const pieOption = useMemo(() => {
    if (objectStats.length === 0) {
      return {
        title: {
          text: '暂无数据',
          left: 'center',
          top: 'center',
          textStyle: { color: '#999', fontSize: 14 },
        },
      };
    }

    return {
      tooltip: {
        trigger: 'item' as const,
        formatter: '{b}: {c} 个 ({d}%)',
      },
      series: [
        {
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['50%', '50%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 6,
            borderColor: '#1a1a2e',
            borderWidth: 2,
          },
          label: {
            show: true,
            formatter: '{b}\n{c}',
            color: '#ccc',
            fontSize: 11,
          },
          labelLine: {
            lineStyle: { color: '#555' },
          },
          data: objectStats.map((s) => ({
            name: s.className,
            value: s.count,
            itemStyle: { color: s.color },
          })),
        },
      ],
    };
  }, [objectStats]);

  // 柱状图配置
  const barOption = useMemo(() => {
    if (objectStats.length === 0) {
      return {
        title: {
          text: '暂无数据',
          left: 'center',
          top: 'center',
          textStyle: { color: '#999', fontSize: 14 },
        },
      };
    }

    return {
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '10%',
        containLabel: true,
      },
      xAxis: {
        type: 'category' as const,
        data: objectStats.map((s) => s.className),
        axisLabel: { color: '#ccc', fontSize: 10, rotate: 30 },
        axisLine: { lineStyle: { color: '#444' } },
      },
      yAxis: {
        type: 'value' as const,
        minInterval: 1,
        axisLabel: { color: '#ccc' },
        splitLine: { lineStyle: { color: '#333' } },
      },
      tooltip: {
        trigger: 'axis' as const,
        formatter: '{b}: {c} 个',
      },
      series: [
        {
          type: 'bar',
          data: objectStats.map((s) => ({
            value: s.count,
            itemStyle: {
              color: s.color,
              borderRadius: [4, 4, 0, 0],
            },
          })),
          barWidth: '60%',
        },
      ],
    };
  }, [objectStats]);

  return (
    <div className="panel stats-panel">
      <div className="panel-header">
        <span className="panel-icon">📊</span>
        <span className="panel-title">对象实时统计</span>
        <span className="panel-badge">{detections.length} 个对象</span>
      </div>

      <div className="stats-content">
        {/* 对象列表 */}
        <div className="stats-list">
          {!isCameraOn ? (
            <div className="stats-empty">
              <p>摄像头未开启</p>
              <p className="stats-empty-sub">开启摄像头后显示检测结果</p>
            </div>
          ) : objectStats.length === 0 ? (
            <div className="stats-empty">
              <p>未检测到对象</p>
              <p className="stats-empty-sub">请调整摄像头角度</p>
            </div>
          ) : (
            objectStats.map((stat) => (
              <div key={stat.className} className="stats-item">
                <div className="stats-item-header">
                  <span
                    className="stats-dot"
                    style={{ backgroundColor: stat.color }}
                  />
                  <span className="stats-name">{stat.className}</span>
                  <span className="stats-count">{stat.count}</span>
                </div>
                <div className="stats-bar-bg">
                  <div
                    className="stats-bar-fill"
                    style={{
                      width: `${Math.min(
                        (stat.count / Math.max(...objectStats.map((s) => s.count))) * 100,
                        100
                      )}%`,
                      backgroundColor: stat.color,
                    }}
                  />
                </div>
              </div>
            ))
          )}
        </div>

        {/* 图表区域 */}
        <div className="stats-charts">
          <div className="stats-chart-item">
            <div className="stats-chart-title">对象分布</div>
            <ReactEChartsCore
              echarts={echarts}
              option={pieOption}
              style={{ height: 180 }}
              notMerge
            />
          </div>
          <div className="stats-chart-item">
            <div className="stats-chart-title">数量对比</div>
            <ReactEChartsCore
              echarts={echarts}
              option={barOption}
              style={{ height: 180 }}
              notMerge
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatsPanel;
