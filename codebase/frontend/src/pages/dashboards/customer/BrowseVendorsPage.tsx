import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, MapPin, ShoppingBag, Store, Navigation, Star, ChevronLeft, ChevronRight } from "lucide-react";
import { DashboardLayout } from "../../../layouts/DashboardLayout";
import { Card, CardBody } from "../../../components/ui/Card";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { EmptyState } from "../../../components/ui/EmptyState";
import { useToast } from "../../../context/ToastContext";
import { addressService } from "../../../services/addressService";
import { catalogService } from "../../../services/catalogService";
import type { CustomerAddress } from "../../../types/catalog";
import type { Branch } from "../../../types/catalog";
import { SkeletonList } from "../../../components/ui/Skeleton";

type SortOption = "distance" | "rating" | "name";

function formatDistance(meters?: number): string | null {
  if (meters === undefined) return null;
  if (meters < 1000) return `${Math.round(meters)} m away`;
  return `${(meters / 1000).toFixed(1)} km away`;
}

export function BrowseVendorsPage() {
  const { showError } = useToast();
  const [addresses, setAddresses] = useState<CustomerAddress[]>([]);
  const [selectedAddressId, setSelectedAddressId] = useState<string>("");
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortOption>("distance");
  const [minRating, setMinRating] = useState("");
  const [branches, setBranches] = useState<Branch[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loadingAddresses, setLoadingAddresses] = useState(true);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    addressService
      .list()
      .then((list) => {
        setAddresses(list);
        const preferred = list.find((a) => a.is_default) ?? list[0];
        if (preferred) {
          setSelectedAddressId(preferred.id);
          setCoords({ lat: preferred.latitude, lng: preferred.longitude });
        }
      })
      .catch(() => showError("Could not load your saved addresses."))
      .finally(() => setLoadingAddresses(false));
  }, [showError]);

  // Any change to the search criteria (not just pagination) should return
  // the customer to page 1 rather than silently keeping them on a page
  // that may no longer exist for the new result set.
  useEffect(() => {
    setPage(1);
  }, [coords, search, sort, minRating]);

  useEffect(() => {
    if (!coords) return;
    setSearching(true);
    catalogService
      .discoverBranches(coords.lat, coords.lng, {
        search: search || undefined,
        sort,
        minRating: minRating ? Number(minRating) : undefined,
        page,
        perPage: 12,
      })
      .then((result) => {
        setBranches(result.branches);
        setTotalPages(result.pagination.total_pages || 1);
      })
      .catch(() => showError("Could not search for nearby vendors."))
      .finally(() => setSearching(false));
  }, [coords, search, sort, minRating, page, showError]);

  const handleAddressChange = (addressId: string) => {
    setSelectedAddressId(addressId);
    const address = addresses.find((a) => a.id === addressId);
    if (address) setCoords({ lat: address.latitude, lng: address.longitude });
  };

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      showError("Location is not available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setSelectedAddressId("");
        setCoords({ lat: position.coords.latitude, lng: position.coords.longitude });
      },
      () => showError("Could not get your current location.")
    );
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Browse vendors</h1>
          <p className="text-ink-soft mt-1">Discover local shops and restaurants that deliver to you.</p>
        </div>

        <Card>
          <CardBody className="space-y-4">
            {loadingAddresses ? (
              <SkeletonList />
            ) : addresses.length === 0 ? (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-ink-soft">
                  Save an address to search from it, or{" "}
                  <button onClick={useMyLocation} className="text-primary font-medium underline underline-offset-2">
                    use your current location
                  </button>
                  .
                </p>
                <Link to="/customer/dashboard/addresses">
                  <Button variant="secondary" size="sm">
                    <MapPin className="h-3.5 w-3.5" />
                    Add address
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="grid sm:grid-cols-[1fr_auto] gap-3 items-end">
                <Select
                  label="Searching from"
                  value={selectedAddressId}
                  onChange={(e) => handleAddressChange(e.target.value)}
                >
                  {addresses.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.label} - {a.city}
                    </option>
                  ))}
                </Select>
                <Button variant="secondary" onClick={useMyLocation}>
                  <Navigation className="h-3.5 w-3.5" />
                  Use current location
                </Button>
              </div>
            )}

            {coords && (
              <div className="grid sm:grid-cols-[1fr_auto_auto] gap-3 items-end">
                <Input
                  label="Search"
                  icon={<Search className="h-4 w-4" />}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search vendors or branches..."
                />
                <div className="w-40">
                  <Select label="Sort by" value={sort} onChange={(e) => setSort(e.target.value as SortOption)}>
                    <option value="distance">Nearest</option>
                    <option value="rating">Top rated</option>
                    <option value="name">Name (A-Z)</option>
                  </Select>
                </div>
                <div className="w-36">
                  <Select label="Minimum rating" value={minRating} onChange={(e) => setMinRating(e.target.value)}>
                    <option value="">Any rating</option>
                    <option value="3">3+ stars</option>
                    <option value="4">4+ stars</option>
                    <option value="4.5">4.5+ stars</option>
                  </Select>
                </div>
              </div>
            )}
          </CardBody>
        </Card>

        {!coords ? null : searching ? (
          <SkeletonList />
        ) : branches.length === 0 ? (
          <EmptyState
            icon={<ShoppingBag className="h-5 w-5" />}
            title="No vendors deliver here yet"
            description="Try a different address or a lower minimum rating, or check back soon as more vendors join."
          />
        ) : (
          <>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {branches.map((branch) => (
                <Link key={branch.id} to={`/customer/dashboard/vendors/${branch.vendor_id}/branches/${branch.id}`}>
                  <Card className="h-full transition-shadow hover:shadow-md">
                    <CardBody className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 text-primary min-w-0">
                          <Store className="h-4 w-4 shrink-0" />
                          <p className="font-medium text-ink truncate">{branch.vendor_name ?? branch.name}</p>
                        </div>
                        {branch.vendor_rating_average != null && (
                          <div className="flex items-center gap-1 text-xs text-ink-soft shrink-0">
                            <Star className="h-3.5 w-3.5 fill-warning text-warning" />
                            {branch.vendor_rating_average.toFixed(1)}
                          </div>
                        )}
                      </div>
                      <p className="text-sm text-ink-soft">{branch.name}</p>
                      <p className="text-xs text-ink-soft">{branch.address}</p>
                      {formatDistance(branch.distance_meters) && (
                        <p className="text-xs text-ink-soft">{formatDistance(branch.distance_meters)}</p>
                      )}
                    </CardBody>
                  </Card>
                </Link>
              ))}
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3">
                <Button variant="secondary" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                  <ChevronLeft className="h-3.5 w-3.5" />
                  Previous
                </Button>
                <span className="text-sm text-ink-soft">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                >
                  Next
                  <ChevronRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
