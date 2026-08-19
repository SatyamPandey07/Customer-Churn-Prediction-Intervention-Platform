"use client";

import React, { createContext, useContext, useEffect, useState } from 'react';

interface TenantBranding {
  tenant_id: string;
  logo_url?: string;
  primary_color?: string;
  secondary_color?: string;
  favicon_url?: string;
  product_display_name?: string;
  support_contact_email?: string;
}

interface BrandingContextValue {
  branding: TenantBranding | null;
  loading: boolean;
}

const BrandingContext = createContext<BrandingContextValue>({ branding: null, loading: true });

export function TenantBrandingProvider({ children }: { children: React.ReactNode }) {
  const [branding, setBranding] = useState<TenantBranding | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchBranding = async () => {
      try {
        const domain = window.location.hostname;
        const res = await fetch(`http://localhost:8000/branding/public?domain=${encodeURIComponent(domain)}`);
        
        if (res.ok) {
          const data = await res.json();
          if (data) {
            setBranding(data);
            
            // Apply CSS Variables
            const root = document.documentElement;
            if (data.primary_color) {
              root.style.setProperty('--tenant-primary', data.primary_color);
            }
            if (data.secondary_color) {
              root.style.setProperty('--tenant-secondary', data.secondary_color);
            }
            if (data.favicon_url) {
              let link = document.querySelector("link[rel~='icon']") as HTMLLinkElement;
              if (!link) {
                link = document.createElement('link');
                link.rel = 'icon';
                document.head.appendChild(link);
              }
              link.href = data.favicon_url;
            }
            if (data.product_display_name) {
              document.title = data.product_display_name;
            }
          }
        }
      } catch (e) {
        console.error("Failed to fetch tenant branding", e);
      } finally {
        setLoading(false);
      }
    };
    
    fetchBranding();
  }, []);

  return (
    <BrandingContext.Provider value={{ branding, loading }}>
      {children}
    </BrandingContext.Provider>
  );
}

export function useTenantBranding() {
  return useContext(BrandingContext);
}
