import React from 'react';

const BentoCard = ({ title, subtitle, content, color, icon: Icon, className = "", onClick }) => {
  return (
    <div 
      onClick={onClick}
      className={`
      ${color} border-4 border-black p-6 shadow-brutal 
      hover:translate-x-[4px] hover:translate-y-[4px] hover:shadow-none 
      transition-all cursor-pointer flex flex-col justify-between
      ${className}
    `}>
      <div>
        <div className="flex justify-between items-start mb-4">
          <h3 className="text-2xl font-black uppercase leading-none">{title}</h3>
          {Icon && <Icon size={32} strokeWidth={3} />}
        </div>
        <p className="font-bold text-sm uppercase mb-2 opacity-80">{subtitle}</p>
        <div className="font-medium leading-tight">{content}</div>
      </div>
      
      <div className="mt-4 pt-4 border-t-2 border-black flex justify-between items-center">
        <span className="text-xs font-black uppercase italic">Détails studio</span>
        <div className="w-8 h-8 bg-black flex items-center justify-center text-white">
          →
        </div>
      </div>
    </div>
  );
};

export default BentoCard;