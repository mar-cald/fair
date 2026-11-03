data { int N; vector[N] rt; }
parameters { real mu; real<lower=0> sigma; }
model { rt ~ lognormal(mu, sigma); }
