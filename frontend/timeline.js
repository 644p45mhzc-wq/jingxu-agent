// Reference months for planning, not confirmed dates. Include this month + 11.
window.RegistrationTimeline = {
  range(today) {
    const [y,m] = today.split('-').map(Number);
    const endDate = new Date(Date.UTC(y,m-1+11,1));
    return {start:`${y}-${String(m).padStart(2,'0')}`, end:`${endDate.getUTCFullYear()}-${String(endDate.getUTCMonth()+1).padStart(2,'0')}`};
  },
  entries(contests, today) {
    const [year,month] = today.split('-').map(Number);
    return contests.flatMap(c => {
      const ref = c.registration_reference;
      if (!ref || !Number.isInteger(ref.month) || ref.month < 1 || ref.month > 12) return [];
      const eventYear = ref.month >= month ? year : year + 1;
      if (ref.parity !== undefined && eventYear % 2 !== ref.parity) return [];
      return [{contest:c, date:`${eventYear}-${String(ref.month).padStart(2,'0')}`, year:eventYear, label:ref.label, reference:true}];
    }).sort((a,b) => a.date.localeCompare(b.date) || a.contest.name.localeCompare(b.contest.name));
  }
};
