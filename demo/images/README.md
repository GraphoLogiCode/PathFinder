# PathFinder Demo Images — Most Damaged Satellite Images

Raw satellite images from the xBD dataset, ranked by AI-detected damage severity.
Upload any of these to the PathFinder app to test damage detection.

## Image Catalog

| # | File | Location | GPS (lat, lng) | Damage |
|---|------|----------|----------------|--------|
| 01 | `01_tubbs-fire_66-destroyed.png` | Santa Rosa, CA, USA | **38.4404, -122.7141** | 🔴 66 destroyed |
| 02 | `02_tubbs-fire_27-destroyed.png` | Santa Rosa, CA, USA | **38.4404, -122.7141** | 🔴 27 destroyed |
| 03 | `03_tubbs-fire_13-destroyed.png` | Santa Rosa, CA, USA | **38.4404, -122.7141** | 🔴 13 destroyed |
| 04 | `04_hurricane-harvey_39-major.png` | Houston, TX, USA | **29.7604, -95.3698** | 🟠 39 major-damage |
| 05 | `05_hurricane-harvey_26-major.png` | Houston, TX, USA | **29.7604, -95.3698** | 🟠 26 major-damage |
| 06 | `06_hurricane-florence_16-major.png` | Wilmington, NC, USA | **34.2257, -78.0447** | 🟠 16 major-damage |
| 07 | `07_hurricane-florence_48-major.png` | Wilmington, NC, USA | **34.2257, -78.0447** | 🟠 48 major-damage |
| 08 | `08_hurricane-florence_32-major.png` | Wilmington, NC, USA | **34.2257, -78.0447** | 🟠 32 major-damage |
| 09 | `09_hurricane-michael_20-minor.png` | Mexico Beach, FL, USA | **30.1588, -85.6602** | 🟡 20 minor-damage |
| 10 | `10_hurricane-harvey_19-major.png` | Houston, TX, USA | **29.7604, -95.3698** | 🟠 19 major-damage |

## Disaster Details

### 🔴 Tubbs Fire (Images 01–03)
- **Location:** Santa Rosa / Napa Valley, California
- **GPS:** 38.4404, -122.7141
- **Date:** October 8, 2017
- **Type:** Wildfire
- **Impact:** Burned through Coffey Park and Fountaingrove neighborhoods, destroying 5,636 structures

### 🟠 Hurricane Harvey (Images 04, 05, 10)
- **Location:** Houston / Port Aransas, Texas
- **GPS:** 29.7604, -95.3698
- **Date:** August 25, 2017
- **Type:** Hurricane (Category 4)
- **Impact:** 60+ inches of rain, displaced 30,000+ people, damaged 204,000 homes

### 🟠 Hurricane Florence (Images 06–08)
- **Location:** Leland / Wilmington, North Carolina
- **GPS:** 34.2257, -78.0447
- **Date:** September 14, 2018
- **Type:** Hurricane (Category 1)
- **Impact:** Catastrophic freshwater flooding, $24B+ in damage across the Carolinas

### 🟡 Hurricane Michael (Image 09)
- **Location:** Mexico Beach / Panama City, Florida
- **GPS:** 30.1588, -85.6602
- **Date:** October 10, 2018
- **Type:** Hurricane (Category 5)
- **Impact:** Strongest hurricane ever to hit the Florida panhandle, 9–14 ft storm surge

## Usage
1. Open PathFinder app → Click **Upload Image**
2. Pick any image from this folder (start with `01` for best results)
3. Set the map anchor to the GPS coordinates listed above
4. The AI will detect damage polygons and geo-reference them onto the map
