export function RouteNetworkGraphic() {
  return (
    <svg viewBox="0 0 480 460" fill="none" className="w-full h-auto max-w-md" role="img" aria-label="Diagram showing customers, businesses, and riders connected through the Routeley platform">
      <rect x="0" y="0" width="480" height="460" rx="18" fill="#16332A" />

      {/* connecting routes */}
      <path d="M110 100 C 180 140, 200 200, 240 230" stroke="#3E7A64" strokeWidth="2" strokeDasharray="1 7" strokeLinecap="round" />
      <path d="M400 110 C 320 150, 290 200, 240 230" stroke="#3E7A64" strokeWidth="2" strokeDasharray="1 7" strokeLinecap="round" />
      <path d="M240 230 C 230 290, 210 330, 150 370" stroke="#3E7A64" strokeWidth="2" strokeDasharray="1 7" strokeLinecap="round" />
      <path d="M240 230 C 260 290, 290 330, 350 365" stroke="#ff6a39" strokeWidth="2.4" strokeLinecap="round" />

      {/* customer node */}
      <circle cx="110" cy="100" r="26" fill="#1F493B" />
      <circle cx="110" cy="100" r="26" stroke="#3E7A64" />
      <path d="M110 88a7 7 0 100 14 7 7 0 000-14zM97 118c2.8-6.4 8-9.6 13-9.6s10.2 3.2 13 9.6" stroke="#EAF4EF" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <text x="110" y="146" textAnchor="middle" fill="#B9CFC5" fontSize="12" fontFamily="Inter, sans-serif">Customer</text>

      {/* vendor node */}
      <circle cx="400" cy="110" r="26" fill="#1F493B" />
      <circle cx="400" cy="110" r="26" stroke="#3E7A64" />
      <path d="M389 103l2-8h18l2 8M389 103h22v16a2 2 0 01-2 2h-18a2 2 0 01-2-2v-16z" stroke="#EAF4EF" strokeWidth="1.8" strokeLinejoin="round" fill="none" />
      <text x="400" y="156" textAnchor="middle" fill="#B9CFC5" fontSize="12" fontFamily="Inter, sans-serif">Business</text>

      {/* platform node (center) */}
      <circle cx="240" cy="230" r="34" fill="#ff6a39" />
      <path d="M240 214v32M226 222l14-8 14 8M226 238l14 8 14-8" stroke="#16332A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <text x="240" y="282" textAnchor="middle" fill="#F6F6F3" fontSize="13" fontFamily="Space Grotesk, sans-serif" fontWeight="600">Routeley</text>

      {/* rider node */}
      <circle cx="350" cy="365" r="26" fill="#1F493B" />
      <circle cx="350" cy="365" r="26" stroke="#3E7A64" />
      <path d="M338 372l6-16h6l-4 10h10l-14 16 3-10h-7z" fill="#EAF4EF" />
      <text x="350" y="411" textAnchor="middle" fill="#B9CFC5" fontSize="12" fontFamily="Inter, sans-serif">Rider</text>

      {/* second customer-ish node bottom-left to balance composition */}
      <circle cx="150" cy="370" r="18" fill="#1F493B" stroke="#3E7A64" />
      <path d="M150 361a5 5 0 100 10 5 5 0 000-10zM141 376c2-4.6 5.7-6.9 9-6.9s7 2.3 9 6.9" stroke="#EAF4EF" strokeWidth="1.5" strokeLinecap="round" fill="none" />
    </svg>
  );
}
