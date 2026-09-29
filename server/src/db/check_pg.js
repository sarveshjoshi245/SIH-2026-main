import pg from 'pg';
const { Pool } = pg;

async function inspect(dbName) {
  const pool = new Pool({ connectionString: `postgresql://postgres:Ajinkya%401115@localhost:5432/${dbName}` });
  try {
    const tables = await pool.query("SELECT table_name FROM information_schema.tables WHERE table_schema='public'");
    console.log(`\n=== Database: ${dbName} ===`);
    for (const t of tables.rows) {
      const count = await pool.query(`SELECT count(*) FROM ${t.table_name}`);
      const rows = await pool.query(`SELECT * FROM ${t.table_name} LIMIT 5`);
      console.log(`\n-- Table: ${t.table_name} (Total rows: ${count.rows[0].count}) --`);
      console.log(JSON.stringify(rows.rows, null, 2));
    }
  } catch (e) {
    console.error(`Error in ${dbName}:`, e.message);
  } finally {
    await pool.end();
  }
}

async function main() {
  await inspect('interop_platform');
  await inspect('land_department');
  await inspect('pollution_department');
  await inspect('electricity_department');
}

main();
