const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function detectDamage(imageFile: File) {
    const formData = new FormData();
    formData.append("file", imageFile); // Backend expects field name "file"
    const res = await fetch(`${API_BASE}/detect`, { method: "POST", body: formData });
    if (!res.ok) throw new Error(`Detection failed: ${res.statusText}`);
    return res.json();
}

export async function geoReference(
    detections: any[],
    anchor: { lat: number; lng: number },
    scale: number,
    imageCenterPx: number[]
) {
    const res = await fetch(`${API_BASE}/georef`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ detections, anchor, scale, image_center_px: imageCenterPx }),
    });
    if (!res.ok) throw new Error(`Geo-referencing failed: ${res.statusText}`);
    return res.json();
}

export async function calculateRoute(
    start: [number, number], // [lng, lat]
    end: [number, number],   // [lng, lat]
    dangerZones: any,
    mode: string = "pedestrian"
) {
    const res = await fetch(`${API_BASE}/route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            start: { lat: start[1], lng: start[0] },
            end: { lat: end[1], lng: end[0] },
            danger_zones: dangerZones,
            mode,
        }),
    });
    if (!res.ok) throw new Error(`Routing failed: ${res.statusText}`);
    return res.json();
}

export async function saveMission(data: {
    name: string;
    start?: [number, number] | null;
    end?: [number, number] | null;
    detections?: any[];
    dangerZones?: any;
    route?: any;
}) {
    const res = await fetch(`${API_BASE}/missions/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: data.name,
            start: data.start ? { lat: data.start[1], lng: data.start[0] } : null,
            end: data.end ? { lat: data.end[1], lng: data.end[0] } : null,
            detections: data.detections ?? null,
            danger_zones: data.dangerZones ?? null,
            route: data.route ?? null,
        }),
    });
    if (!res.ok) throw new Error(`Save failed: ${res.statusText}`);
    return res.json();
}

export async function getMissions() {
    const res = await fetch(`${API_BASE}/missions/`);
    if (!res.ok) throw new Error(`Failed to load missions: ${res.statusText}`);
    return res.json();
}

export async function getMission(id: string) {
    const res = await fetch(`${API_BASE}/missions/${id}`);
    if (!res.ok) throw new Error(`Mission not found: ${res.statusText}`);
    return res.json();
}