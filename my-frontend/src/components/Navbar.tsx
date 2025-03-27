import React, { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Menu, X, Dumbbell, ShoppingBag, UserPlus, LogIn, LogOut, User } from "lucide-react";
import CreateProfile from "./CreateProfile";
import Login from "./Login";

const Navbar: React.FC = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isCreateProfileOpen, setIsCreateProfileOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const location = useLocation();

  // Check login state on component mount
  useEffect(() => {
    const loginState = localStorage.getItem('isLoggedIn');
    if (loginState === 'true') {
      setIsLoggedIn(true);
    }
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 10) {
        setIsScrolled(true);
      } else {
        setIsScrolled(false);
      }
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    // Close mobile menu when route changes
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  const handleCreateProfile = (profileData: any) => {
    // For now, we'll just log the data
    console.log('Creating profile:', profileData);
    // In the future, this will make an API call to create the profile
  };

  const handleLogin = (loginData: any) => {
    // For now, we'll just log the data
    console.log('Logging in:', loginData);
    // In the future, this will make an API call to login
    setIsLoggedIn(true);
    localStorage.setItem('isLoggedIn', 'true');
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    localStorage.removeItem('isLoggedIn');
    // In the future, this will make an API call to logout
  };

  const links = [
    { href: "/", label: "Home" },
    { href: "/competitions", label: "Competitions" },
    { href: "/athletes", label: "Athletes" },
    { href: "/leaderboard", label: "Leaderboard" },
    { href: "/store", label: "Store", icon: <ShoppingBag className="w-4 h-4" /> },
    { href: "/about", label: "About" },
  ];

  const AuthButton = () => {
    if (isLoggedIn) {
      return (
        <div className="flex items-center gap-4">
          <Link
            to="/profile"
            className="flex items-center gap-2 px-3 py-2 text-foreground/70 hover:text-foreground transition-colors"
          >
            <User size={18} />
            <span>My Profile</span>
          </Link>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-3 py-2 text-accent hover:text-accent/90 transition-colors"
          >
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        </div>
      );
    }

    return (
      <div className="flex items-center gap-4">
        <button
          onClick={() => setIsLoginOpen(true)}
          className="flex items-center gap-2 px-3 py-2 text-foreground/70 hover:text-foreground transition-colors"
        >
          <LogIn size={18} />
          <span>Login</span>
        </button>
        <button
          onClick={() => setIsCreateProfileOpen(true)}
          className="flex items-center gap-2 px-3 py-2 text-accent hover:text-accent/90 transition-colors"
        >
          <UserPlus size={18} />
          <span>Create Profile</span>
        </button>
      </div>
    );
  };

  return (
    <>
      <header
        className={`sticky top-0 z-50 w-full transition-all duration-300 ${
          isScrolled
            ? "bg-background/80 backdrop-blur-md border-b border-border/40 shadow-sm"
            : "bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center space-x-3">
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3 }}
                className="flex items-center gap-2"
              >
                <Dumbbell size={28} className="text-accent" />
                <span className="font-bold text-xl tracking-tight">Tom's Gym</span>
              </motion.div>
            </Link>

            <nav className="hidden md:flex items-center space-x-8">
              {links.map((item, index) => (
                <NavLink
                  key={item.label}
                  to={item.href}
                  label={item.label}
                  isActive={
                    (item.label === "Home" && location.pathname === "/") ||
                    (item.label !== "Home" && location.pathname.includes(item.label.toLowerCase()))
                  }
                  delay={index * 0.1}
                />
              ))}
              <AuthButton />
            </nav>

            <div className="flex md:hidden">
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="text-foreground/70 hover:text-foreground focus:outline-none"
                aria-label="Toggle menu"
              >
                {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile menu */}
      {isMobileMenuOpen && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3 }}
          className="md:hidden bg-background/95 backdrop-blur-md border-b border-border/40"
        >
          <div className="px-4 py-3 space-y-2">
            {links.map((item) => (
              <Link
                key={item.label}
                to={item.href}
                className={`block px-3 py-2 rounded-md text-base font-medium ${
                  (item.label === "Home" && location.pathname === "/") ||
                  (item.label !== "Home" && location.pathname.includes(item.label.toLowerCase()))
                    ? "text-accent font-semibold"
                    : "text-foreground/70 hover:text-foreground hover:bg-secondary/50"
                }`}
              >
                {item.label}
              </Link>
            ))}
            {isLoggedIn ? (
              <>
                <Link
                  to="/profile"
                  className="flex items-center gap-2 px-3 py-2 text-foreground/70 hover:text-foreground transition-colors"
                >
                  <User size={18} />
                  <span>My Profile</span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-3 py-2 text-accent hover:text-accent/90 transition-colors"
                >
                  <LogOut size={18} />
                  <span>Logout</span>
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setIsLoginOpen(true)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-foreground/70 hover:text-foreground transition-colors"
                >
                  <LogIn size={18} />
                  <span>Login</span>
                </button>
                <button
                  onClick={() => setIsCreateProfileOpen(true)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-accent hover:text-accent/90 transition-colors"
                >
                  <UserPlus size={18} />
                  <span>Create Profile</span>
                </button>
              </>
            )}
          </div>
        </motion.div>
      )}

      {/* Create Profile Modal */}
      {isCreateProfileOpen && (
        <CreateProfile
          onClose={() => setIsCreateProfileOpen(false)}
          onSubmit={handleCreateProfile}
        />
      )}

      {/* Login Modal */}
      {isLoginOpen && (
        <Login
          onClose={() => setIsLoginOpen(false)}
          onSubmit={handleLogin}
        />
      )}
    </>
  );
};

interface NavLinkProps {
  to: string;
  label: string;
  isActive: boolean;
  delay?: number;
}

const NavLink: React.FC<NavLinkProps> = ({ to, label, isActive, delay = 0 }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
    >
      <Link
        to={to}
        className={`relative px-1 py-2 transition-colors duration-200 ${
          isActive ? "text-accent font-medium" : "text-foreground/70 hover:text-foreground"
        }`}
      >
        {label}
        {isActive && (
          <motion.div
            layoutId="navbar-indicator"
            className="absolute -bottom-1 left-0 right-0 h-0.5 bg-accent"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          />
        )}
      </Link>
    </motion.div>
  );
};

export default Navbar;
