// Modern sequential color palette similar to Plotly/D3
export const chartColors = [
  '#1f77b4', // blue
  '#ff7f0e', // orange  
  '#2ca02c', // green
  '#d62728', // red
  '#9467bd', // purple
  '#8c564b', // brown
  '#e377c2', // pink
  '#7f7f7f', // gray
  '#bcbd22', // olive
  '#17becf', // cyan
  '#aec7e8', // light blue
  '#ffbb78', // light orange
  '#98df8a', // light green
  '#ff9896', // light red
  '#c5b0d5', // light purple
  '#c49c94', // light brown
  '#f7b6d3', // light pink
  '#c7c7c7', // light gray
  '#dbdb8d', // light olive
  '#9edae5'  // light cyan
]

export function getChartColor(index: number): string {
  return chartColors[index % chartColors.length]
}