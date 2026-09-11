import csv from "./range.csv";

export default {
  fetch() {
    return new Response(csv, {
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Cache-Control": "public, max-age=0, must-revalidate",
        "X-IB-Content": "geofeed",
      },
    });
  },
};
