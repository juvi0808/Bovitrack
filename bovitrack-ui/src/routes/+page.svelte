<script lang="ts">
  import { onMount } from 'svelte';

  // --- 1. Update our data variables ---
  // 'summary' will hold the herd-level KPIs. It starts as an empty object.
  let summary: any = {};
  // 'animals' will hold the list of active animals.
  let animals: any[] = [];

  let isLoading = true;
  let errorMessage = '';

  onMount(async () => {
    try {
      // --- 2. Call the new "Active Summary" endpoint ---
      const response = await fetch('http://127.0.0.1:5000/api/farm/1/stock/active_summary');

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();

      // --- 3. Store the data in our new variables ---
      // The 'data' object from the API has 'summary_kpis' and 'animals' keys.
      summary = data.summary_kpis;
      animals = data.animals;

    } catch (e: any) {
      errorMessage = `Failed to fetch data: ${e.message}`;
      console.error(e);
    } finally {
      isLoading = false;
    }
  });
</script>

<main>
  <h1>Active Stock Summary (Farm 1)</h1>

  {#if isLoading}
    <p>Loading summary data...</p>
  {:else if errorMessage}
    <p class="error">{errorMessage}</p>
  {:else}
    <!-- 4. NEW: Display the Summary KPI section -->
    <div class="summary-grid">
      <div class="kpi-card">
        <span class="value">{summary.total_active_animals}</span>
        <span class="label">Total Animals</span>
      </div>
      <div class="kpi-card">
        <span class="value">{summary.number_of_males} M / {summary.number_of_females} F</span>
        <span class="label">Males / Females</span>
      </div>
      <div class="kpi-card">
        <span class="value">{summary.average_age_months}</span>
        <span class="label">Avg. Age (Months)</span>
      </div>
      <div class="kpi-card">
        <span class="value">{summary.average_gmd_kg_day}</span>
        <span class="label">Avg. GMD (kg/day)</span>
      </div>
      <div class="kpi-card">
        <span class="value">{summary.average_forecasted_weight_kg} kg</span>
        <span class="label">Avg. Forecasted Weight</span>
      </div>
    </div>

    <!-- 5. UPGRADED: The main table of active animals -->
    <h2>Animal Details</h2>
    <table>
      <thead>
        <tr>
          <th>Ear Tag</th>
          <th>Lot</th>
          <th>Race</th>
          <th>Sex</th>
          <th>Entry Date</th>
          <th>Current Age (Mo)</th>
          <th>Current Location</th>
          <th>Last Weight (kg)</th>
          <th>Last Weight Date</th>
          <th>GMD (kg/day)</th>
          <th>Forecasted Weight (kg)</th>
        </tr>
      </thead>
      <tbody>
        {#each animals as animal}
          <tr>
            <td>{animal.ear_tag}</td>
            <td>{animal.lot}</td>
            <td>{animal.race || 'N/A'}</td>
            <td>{animal.sex}</td>
            <td>{animal.entry_date}</td>
            <td>{animal.kpis.current_age_months}</td>
            <td>{animal.kpis.current_location_name || 'Unknown'}</td>
            <td>{animal.kpis.last_weight_kg}</td>
            <td>{animal.kpis.last_weighting_date}</td>
            <td>{animal.kpis.average_daily_gain_kg}</td>
            <td>{animal.kpis.forecasted_current_weight_kg}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</main>

<!-- Add some new styles for our summary cards -->
<style>
  main {
    padding: 5rem;
    font-family: sans-serif;
    max-width: 1300px;
    margin: auto;
  }
  h1, h2 {
    color: #333;
  }
  .error {
    color: red;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .kpi-card {
    background-color: #f2f2f2;
    border: 1px solid #ffffff;
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
    display: flex;
    flex-direction: column;
  }

  .kpi-card .value {
    font-size: 2rem;
    font-weight: bold;
    color: #2c3e50;
  }

  .kpi-card .label {
    font-size: 0.9rem;
    color: #7f8c8d;
    margin-top: 0.5rem;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 1rem;
  }
  th, td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: center;
  }
  th {
    background-color: #f2f2f2;
  }
</style>```