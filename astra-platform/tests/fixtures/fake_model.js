// Stand-in for the Python inference scripts in tests. It is run by the Node binary in place of
// the Python interpreter and echoes back exactly what it received, so tests can check that
// arguments arrive verbatim (no shell) and that the route only returns real "model" output.
const args = process.argv.slice(2);
let stdin = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => (stdin += chunk));
process.stdin.on('end', () => {
  const mode = process.env.FAKE_MODEL_MODE || 'ok';
  if (mode === 'error') {
    console.log(JSON.stringify({ error: 'model crashed' }));
    process.exit(1);
  }
  if (mode === 'garbage') {
    console.log('not json at all');
    return;
  }
  if (mode === 'bad_payload') {
    console.log(JSON.stringify({ predicted_class: 'quasar', probabilities: {} }));
    return;
  }
  if (mode === 'hang') {
    setTimeout(() => undefined, 60_000);
    return;
  }
  console.log(
    JSON.stringify({
      predicted_class: 'cepheid',
      calibrated_confidence: 0.6,
      entropy: 1.1,
      variance: 0.01,
      probabilities: { rr_lyrae: 0.1, cepheid: 0.6, eclipsing_binary: 0.1, solar_like: 0.1, stable: 0.1 },
      attention_weights: [[1]],
      received_args: args,
      received_stdin: stdin,
    }),
  );
});
