module brain_sha256_compress (
  input  logic [255:0] state_in,
  input  logic [511:0] block_in,
  output logic [255:0] state_out
);
  logic [31:0] w [0:63];
  logic [31:0] k [0:63];
  logic [31:0] a, b, c, d, e, f, g, h;
  logic [31:0] t1, t2;
  integer i;

  function automatic logic [31:0] rotr(input logic [31:0] x, input integer n);
    rotr = (x >> n) | (x << (32-n));
  endfunction

  function automatic logic [31:0] ch(input logic [31:0] x, y, z);
    ch = (x & y) ^ (~x & z);
  endfunction

  function automatic logic [31:0] maj(input logic [31:0] x, y, z);
    maj = (x & y) ^ (x & z) ^ (y & z);
  endfunction

  function automatic logic [31:0] big0(input logic [31:0] x);
    big0 = rotr(x,2) ^ rotr(x,13) ^ rotr(x,22);
  endfunction

  function automatic logic [31:0] big1(input logic [31:0] x);
    big1 = rotr(x,6) ^ rotr(x,11) ^ rotr(x,25);
  endfunction

  function automatic logic [31:0] small0(input logic [31:0] x);
    small0 = rotr(x,7) ^ rotr(x,18) ^ (x >> 3);
  endfunction

  function automatic logic [31:0] small1(input logic [31:0] x);
    small1 = rotr(x,17) ^ rotr(x,19) ^ (x >> 10);
  endfunction

  always_comb begin
    k[0]=32'h428a2f98; k[1]=32'h71374491; k[2]=32'hb5c0fbcf; k[3]=32'he9b5dba5;
    k[4]=32'h3956c25b; k[5]=32'h59f111f1; k[6]=32'h923f82a4; k[7]=32'hab1c5ed5;
    k[8]=32'hd807aa98; k[9]=32'h12835b01; k[10]=32'h243185be; k[11]=32'h550c7dc3;
    k[12]=32'h72be5d74; k[13]=32'h80deb1fe; k[14]=32'h9bdc06a7; k[15]=32'hc19bf174;
    k[16]=32'he49b69c1; k[17]=32'hefbe4786; k[18]=32'h0fc19dc6; k[19]=32'h240ca1cc;
    k[20]=32'h2de92c6f; k[21]=32'h4a7484aa; k[22]=32'h5cb0a9dc; k[23]=32'h76f988da;
    k[24]=32'h983e5152; k[25]=32'ha831c66d; k[26]=32'hb00327c8; k[27]=32'hbf597fc7;
    k[28]=32'hc6e00bf3; k[29]=32'hd5a79147; k[30]=32'h06ca6351; k[31]=32'h14292967;
    k[32]=32'h27b70a85; k[33]=32'h2e1b2138; k[34]=32'h4d2c6dfc; k[35]=32'h53380d13;
    k[36]=32'h650a7354; k[37]=32'h766a0abb; k[38]=32'h81c2c92e; k[39]=32'h92722c85;
    k[40]=32'ha2bfe8a1; k[41]=32'ha81a664b; k[42]=32'hc24b8b70; k[43]=32'hc76c51a3;
    k[44]=32'hd192e819; k[45]=32'hd6990624; k[46]=32'hf40e3585; k[47]=32'h106aa070;
    k[48]=32'h19a4c116; k[49]=32'h1e376c08; k[50]=32'h2748774c; k[51]=32'h34b0bcb5;
    k[52]=32'h391c0cb3; k[53]=32'h4ed8aa4a; k[54]=32'h5b9cca4f; k[55]=32'h682e6ff3;
    k[56]=32'h748f82ee; k[57]=32'h78a5636f; k[58]=32'h84c87814; k[59]=32'h8cc70208;
    k[60]=32'h90befffa; k[61]=32'ha4506ceb; k[62]=32'hbef9a3f7; k[63]=32'hc67178f2;

    for (i=0; i<16; i=i+1)
      w[i] = block_in[511-(i*32) -: 32];
    for (i=16; i<64; i=i+1)
      w[i] = small1(w[i-2]) + w[i-7] + small0(w[i-15]) + w[i-16];

    a=state_in[255:224]; b=state_in[223:192]; c=state_in[191:160]; d=state_in[159:128];
    e=state_in[127:96]; f=state_in[95:64]; g=state_in[63:32]; h=state_in[31:0];
    for (i=0; i<64; i=i+1) begin
      t1 = h + big1(e) + ch(e,f,g) + k[i] + w[i];
      t2 = big0(a) + maj(a,b,c);
      h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
    end
    state_out = {
      state_in[255:224]+a, state_in[223:192]+b,
      state_in[191:160]+c, state_in[159:128]+d,
      state_in[127:96]+e, state_in[95:64]+f,
      state_in[63:32]+g, state_in[31:0]+h
    };
  end
endmodule
