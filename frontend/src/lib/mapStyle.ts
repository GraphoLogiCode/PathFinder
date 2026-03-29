const MAPTILER_KEY = process.env.NEXT_PUBLIC_MAPTILER_KEY || "";

export const SATELLITE_STYLE = `https://api.maptiler.com/maps/satellite/style.json?key=${MAPTILER_KEY}`;
export const STREET_STYLE = `https://api.maptiler.com/maps/basic-v2-dark/style.json?key=${MAPTILER_KEY}`;