import Chart from "react-apexcharts";
import { ApexOptions } from "apexcharts";

// Add props for small, inlineOnly, and oneSeriesOnly
export default function LineChartOne({ small = false, inlineOnly = false, oneSeriesOnly = false }: { small?: boolean; inlineOnly?: boolean; oneSeriesOnly?: boolean }) {
  const options: ApexOptions = {
    legend: {
      show: false, // Hide legend
      position: "top",
      horizontalAlign: "left",
    },
    colors: ["#465FFF", "#9CB9FF"], // Define line colors
    chart: {
      fontFamily: "Outfit, sans-serif",
      height: small ? 32 : 310,
      type: "line", // Set the chart type to 'line'
      toolbar: {
        show: false, // Hide chart toolbar
      },
      sparkline: small || inlineOnly ? { enabled: true } : { enabled: false },
    },
    stroke: {
      curve: "straight", // Define the line style (straight, smooth, or step)
      width: [2, 2], // Line width for each dataset
    },
    fill: {
      type: "gradient",
      gradient: {
        opacityFrom: 0.55,
        opacityTo: 0,
      },
    },
    markers: {
      size: 0, // Size of the marker points
      strokeColors: "#fff", // Marker border color
      strokeWidth: 2,
      hover: {
        size: 6, // Marker size on hover
      },
    },
    grid: {
      xaxis: {
        lines: {
          show: false, // Hide grid lines on x-axis
        },
      },
      yaxis: {
        lines: {
          show: !small && !inlineOnly, // Hide grid lines for sparkline
        },
      },
    },
    dataLabels: {
      enabled: false, // Disable data labels
    },
    tooltip: {
      enabled: !small && !inlineOnly, // Disable tooltip for sparkline
      x: {
        format: "dd MMM yyyy", // Format for x-axis tooltip
      },
    },
    xaxis: {
      type: "category", // Category-based x-axis
      categories: [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
      ],
      axisBorder: {
        show: false, // Hide x-axis border
      },
      axisTicks: {
        show: false, // Hide x-axis ticks
      },
      tooltip: {
        enabled: false, // Disable tooltip for x-axis points
      },
      labels: {
        show: !small && !inlineOnly,
      },
    },
    yaxis: {
      labels: {
        style: {
          fontSize: "12px", // Adjust font size for y-axis labels
          colors: ["#6B7280"], // Color of the labels
        },
        show: !small && !inlineOnly,
      },
      title: {
        text: "", // Remove y-axis title
        style: {
          fontSize: "0px",
        },
      },
    },
  };

  const series = oneSeriesOnly
    ? [
        {
          name: "Leads",
          data: [180, 190, 170, 160, 175, 165, 170, 205, 230, 240, 250, 265],
        },
      ]
    : [
        {
          name: "Sales",
          data: [180, 190, 170, 160, 175, 165, 170, 205, 230, 210, 240, 235],
        },
        {
          name: "Revenue",
          data: [40, 30, 50, 40, 55, 40, 70, 100, 110, 120, 150, 140],
        },
      ];

  return (
    <div className={inlineOnly ? "w-full h-full" : "max-w-full overflow-x-auto custom-scrollbar"}>
      <div id="chartEight" className={inlineOnly ? "w-full h-full" : small ? "min-w-[120px]" : "min-w-[1000px]"}>
        <Chart options={options} series={series} type="area" height={small || inlineOnly ? 32 : 310} />
      </div>
    </div>
  );
}
