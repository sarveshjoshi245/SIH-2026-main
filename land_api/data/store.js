const { Pool } = require('pg');
const seedRecords = require('./landRecords.json');
const divisionsData = require('./divisions.json');
const ferfarData = require('./ferfarData.json');

/**
 * PostgreSQL-backed store with automatic JSON fallback.
 * Loads records directly from the 'land_department' database on startup.
 */
const records = new Map(seedRecords.map((r) => [String(r.gtn), { ...r }]));
const ferfarRecords = new Map(ferfarData.map((f) => [String(f.ferfar_no), { ...f }]));

const VALID_MUTATION_STATUSES = ['PENDING', 'APPROVED', 'REJECTED', 'UNDER_OBJECTION'];

const pgConnectionString = process.env.DATABASE_URL || 'postgresql://postgres:Ajinkya%401115@localhost:5432/land_department';
let pool = null;

try {
  pool = new Pool({ connectionString: pgConnectionString });
  pool.query('SELECT * FROM land_records', (err, res) => {
    if (!err && res && res.rows) {
      res.rows.forEach((r) => {
        const existing = records.get(String(r.gtn)) || {};
        records.set(String(r.gtn), {
          ...existing,
          gtn: String(r.gtn),
          survey_number: String(r.gtn),
          malak_name: r.malak_name || existing.malak_name,
          malak_pan: r.malak_pan || existing.malak_pan,
          kshetra: String(r.kshetra || existing.kshetra || '5.0'),
          kshetra_unit: r.kshetra_unit || 'HA',
          jamabandi: r.jamabandi || existing.jamabandi || 'APPROVED',
          jamin_prakar: r.jamin_prakar || existing.jamin_prakar || 'INDUSTRIAL',
          bandhak: Boolean(r.bandhak),
          court_case: Boolean(r.court_case),
          district: r.district || existing.district || 'Pune',
          taluka: r.taluka || existing.taluka || 'Haveli',
          village: r.village || existing.village || 'Wagholi',
          simulateOutage: Boolean(r.simulate_outage)
        });
      });
      console.log(`[Land API] Connected to PostgreSQL (land_department) — ${res.rows.length} records loaded.`);
    } else if (err) {
      console.warn('[Land API] PostgreSQL query error, using local fallback:', err.message);
    }
  });
} catch (e) {
  console.warn('[Land API] PostgreSQL connection error, using local fallback:', e.message);
}

function getDivisionsData() {
  return divisionsData;
}

async function getRecord(surveyOrPan) {
  const query = String(surveyOrPan).trim();
  if (pool) {
    try {
      const res = await pool.query(
        'SELECT * FROM land_records WHERE gtn = $1 OR UPPER(malak_pan) = UPPER($1) LIMIT 1',
        [query]
      );
      if (res.rows && res.rows.length > 0) {
        const r = res.rows[0];
        const existing = records.get(String(r.gtn)) || {};
        const rec = {
          ...existing,
          gtn: String(r.gtn),
          survey_number: String(r.gtn),
          malak_name: r.malak_name,
          malak_pan: r.malak_pan,
          kshetra: String(r.kshetra),
          kshetra_unit: r.kshetra_unit || 'HA',
          jamabandi: r.jamabandi,
          jamin_prakar: r.jamin_prakar,
          bandhak: Boolean(r.bandhak),
          court_case: Boolean(r.court_case),
          district: r.district,
          taluka: r.taluka,
          village: r.village,
          simulateOutage: Boolean(r.simulate_outage)
        };
        records.set(String(r.gtn), rec);
        return rec;
      }
    } catch (e) {
      console.warn('[Land API] DB getRecord error, falling back to map:', e.message);
    }
  }
  return records.get(query) || Array.from(records.values()).find(r => r.malak_pan?.toUpperCase() === query.toUpperCase()) || null;
}

async function searchMahaBhulekh({ division, district, taluka, village, searchType, query }) {
  const all = Array.from(records.values());
  const q = String(query || '').trim().toLowerCase();

  let filtered = all;

  if (district) {
    filtered = filtered.filter(r => (r.district || '').toLowerCase() === district.toLowerCase() || (r.district_mr || '') === district);
  }
  if (taluka) {
    filtered = filtered.filter(r => (r.taluka || '').toLowerCase() === taluka.toLowerCase() || (r.taluka_mr || '') === taluka);
  }
  if (village) {
    filtered = filtered.filter(r => (r.village || '').toLowerCase() === village.toLowerCase() || (r.village_mr || '') === village);
  }

  if (!q) {
    return filtered;
  }

  return filtered.filter(r => {
    switch (searchType) {
      case 'survey':
      case 'gat':
        return String(r.gtn) === q || String(r.survey_number) === q;
      case 'khata':
        return String(r.khata_no || '') === q;
      case 'pan':
        return (r.malak_pan || '').toLowerCase() === q;
      case 'name':
      default:
        return (r.malak_name || '').toLowerCase().includes(q) ||
               (r.malak_name_en || '').toLowerCase().includes(q) ||
               String(r.gtn) === q;
    }
  });
}

async function get8AExtract(khataOrPanOrName) {
  const query = String(khataOrPanOrName || '').trim().toLowerCase();
  const all = Array.from(records.values());

  const matching = all.filter(r => 
    String(r.khata_no || '') === query ||
    (r.malak_pan || '').toLowerCase() === query ||
    (r.malak_name || '').toLowerCase().includes(query) ||
    (r.malak_name_en || '').toLowerCase().includes(query)
  );

  if (matching.length === 0) return null;

  const first = matching[0];
  const totalArea = matching.reduce((sum, r) => sum + parseFloat(r.kshetra || 0), 0).toFixed(2);
  const totalPotKharaba = matching.reduce((sum, r) => sum + parseFloat(r.pot_kharaba || 0), 0).toFixed(2);
  const totalAakarni = matching.reduce((sum, r) => sum + parseFloat(r.aakarni || 0), 0).toFixed(2);

  return {
    khata_no: first.khata_no || '452',
    malak_name: first.malak_name,
    malak_name_en: first.malak_name_en,
    malak_pan: first.malak_pan,
    malak_aadhaar: first.malak_aadhaar,
    district: first.district,
    taluka: first.taluka,
    village: first.village,
    total_area_hectares: totalArea,
    total_pot_kharaba: totalPotKharaba,
    total_aakarni: totalAakarni,
    holdings: matching.map(r => ({
      survey_number: r.gtn,
      hissa_no: r.hissa_no || '1',
      area_hectares: r.kshetra,
      pot_kharaba: r.pot_kharaba || '0.00',
      aakarni: r.aakarni || '0.00',
      jamin_prakar: r.jamin_prakar_mr || r.jamin_prakar,
      mutation_status: r.jamabandi
    }))
  };
}

async function getFerfarRecords(surveyOrFerfarNo) {
  const query = String(surveyOrFerfarNo || '').trim();
  const all = Array.from(ferfarRecords.values());
  if (!query) return all;

  return all.filter(f => 
    String(f.ferfar_no) === query || 
    String(f.survey_number) === query ||
    (f.village || '').toLowerCase() === query.toLowerCase()
  );
}

async function getAapliChawadiNotices(villageOrTaluka) {
  const query = String(villageOrTaluka || '').trim().toLowerCase();
  const all = Array.from(ferfarRecords.values());
  if (!query) return all.map(f => f.section_135d_notice).filter(Boolean);

  return all
    .filter(f => (f.village || '').toLowerCase().includes(query) || (f.taluka || '').toLowerCase().includes(query))
    .map(f => ({
      ...f.section_135d_notice,
      ferfar_no: f.ferfar_no,
      survey_number: f.survey_number,
      village: f.village,
      taluka: f.taluka,
      district: f.district
    }))
    .filter(Boolean);
}

async function getAllRecords() {
  if (pool) {
    try {
      const res = await pool.query('SELECT * FROM land_records ORDER BY id ASC');
      if (res.rows && res.rows.length > 0) {
        res.rows.forEach(r => {
          const existing = records.get(String(r.gtn)) || {};
          records.set(String(r.gtn), {
            ...existing,
            gtn: String(r.gtn),
            survey_number: String(r.gtn),
            malak_name: r.malak_name,
            malak_pan: r.malak_pan,
            kshetra: String(r.kshetra),
            kshetra_unit: r.kshetra_unit || 'HA',
            jamabandi: r.jamabandi,
            jamin_prakar: r.jamin_prakar,
            bandhak: Boolean(r.bandhak),
            court_case: Boolean(r.court_case),
            district: r.district,
            taluka: r.taluka,
            village: r.village,
            simulateOutage: Boolean(r.simulate_outage)
          });
        });
      }
    } catch (e) {
      console.warn('[Land API] DB getAllRecords error:', e.message);
    }
  }
  return Array.from(records.values());
}

async function saveRecord(rec) {
  const gtn = String(rec.gtn || rec.survey_number);
  const completeRecord = {
    gtn,
    survey_number: gtn,
    hissa_no: rec.hissa_no || '1',
    khata_no: rec.khata_no || '501',
    malak_name: rec.malak_name || rec.applicantName || 'Registered Applicant',
    malak_name_en: rec.malak_name_en || rec.applicantName || 'Registered Applicant',
    malak_pan: String(rec.malak_pan || rec.pan || 'ABCDE1234F').toUpperCase(),
    malak_aadhaar: rec.malak_aadhaar || '998877665544',
    bhogvatadar_varg: rec.bhogvatadar_varg || 'भोगवटादार वर्ग - १ (Occupant Class 1)',
    kshetra: rec.kshetra ? String(rec.kshetra) : '5.00',
    kshetra_unit: 'HA',
    pot_kharaba: rec.pot_kharaba || '0.10',
    aakarni: rec.aakarni || '25.00',
    judi_tax: '0.00',
    jamabandi: rec.jamabandi || 'PENDING',
    jamin_prakar: rec.jamin_prakar || 'INDUSTRIAL',
    jamin_prakar_mr: rec.jamin_prakar_mr || 'अकृषिक - औद्योगिक',
    bandhak: Boolean(rec.bandhak),
    boja_details: rec.boja_details || 'निरंक',
    court_case: Boolean(rec.court_case),
    court_details: rec.court_details || 'निरंक',
    division: rec.division || 'Pune',
    division_mr: rec.division_mr || 'पुणे',
    district: rec.district || 'Pune',
    district_mr: rec.district_mr || 'पुणे',
    taluka: rec.taluka || 'Haveli',
    taluka_mr: rec.taluka_mr || 'हवेली',
    village: rec.village || 'Wagholi',
    village_mr: rec.village_mr || 'वाघोली',
    ferfar_nos: rec.ferfar_nos || ['1501'],
    pending_ferfar: rec.pending_ferfar || 'निरंक',
    last_mutation_date: new Date().toISOString().split('T')[0],
    talathi_name: rec.talathi_name || 'तलाठी कार्यालय',
    crop_data: rec.crop_data || [
      {
        year: '2025-2026',
        season: 'संपूर्ण वर्ष',
        crop_name: 'अकृषिक - औद्योगिक संकुल',
        area: String(rec.kshetra || '5.00'),
        irrigation_source: 'एमआयडीसी पाणीपुरवठा',
        mixed_crop: 'नाही'
      }
    ]
  };

  records.set(gtn, completeRecord);

  if (pool) {
    try {
      await pool.query(
        `INSERT INTO land_records (gtn, malak_name, malak_pan, kshetra, kshetra_unit, jamabandi, jamin_prakar, bandhak, court_case, district, taluka, village)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
         ON CONFLICT (gtn) DO UPDATE SET
           malak_name = EXCLUDED.malak_name,
           malak_pan = EXCLUDED.malak_pan,
           kshetra = EXCLUDED.kshetra,
           jamabandi = EXCLUDED.jamabandi,
           district = EXCLUDED.district,
           taluka = EXCLUDED.taluka,
           village = EXCLUDED.village`,
        [
          gtn,
          completeRecord.malak_name,
          completeRecord.malak_pan,
          parseFloat(completeRecord.kshetra) || 1.0,
          completeRecord.kshetra_unit || 'HA',
          completeRecord.jamabandi || 'PENDING',
          completeRecord.jamin_prakar || 'INDUSTRIAL',
          completeRecord.bandhak ? 1 : 0,
          completeRecord.court_case ? 1 : 0,
          completeRecord.district || 'Pune',
          completeRecord.taluka || 'Haveli',
          completeRecord.village || 'Wagholi'
        ]
      );
    } catch (e) {
      console.warn('[Land API] DB saveRecord error:', e.message);
    }
  }
  return completeRecord;
}

async function updateMutationStatus(surveyNumber, newStatus) {
  const record = await getRecord(surveyNumber);
  if (!record) return null;
  record.jamabandi = newStatus;
  records.set(String(surveyNumber), record);

  if (pool) {
    try {
      await pool.query('UPDATE land_records SET jamabandi = $1 WHERE gtn = $2', [newStatus, String(surveyNumber)]);
    } catch (err) {
      console.warn('[Land API] Failed to persist mutation update to PostgreSQL:', err.message);
    }
  }
  return record;
}

function listSurveyNumbers() {
  return Array.from(records.keys());
}

module.exports = {
  getRecord,
  getAllRecords,
  saveRecord,
  updateMutationStatus,
  listSurveyNumbers,
  getDivisionsData,
  searchMahaBhulekh,
  get8AExtract,
  getFerfarRecords,
  getAapliChawadiNotices,
  VALID_MUTATION_STATUSES
};
